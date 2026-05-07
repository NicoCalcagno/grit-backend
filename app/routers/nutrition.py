import base64
import uuid
from datetime import datetime, date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.nutrition import DietPlan, FoodLog, NutritionInsight, WaterLog
from app.models.user import User
from app.models.workout import WeeklyPlan, WorkoutSession
from app.schemas.nutrition import (
    DietPlanResponse,
    FoodLogCreate,
    FoodLogResponse,
    FoodPhotoRequest,
    InsightResponse,
    NutritionSummaryResponse,
    RegenerateDayRequest,
    WaterLogCreate,
)
from app.services import claude_service

router = APIRouter(prefix="/nutrition", tags=["nutrition"])

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def get_supabase():
    return create_client(settings.supabase_url, settings.supabase_service_key)


async def _get_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return user


# ── Food Log ───────────────────────────────────────────────────────────────────

@router.post("/logs", response_model=FoodLogResponse, status_code=201)
async def create_food_log(
    body: FoodLogCreate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    log = FoodLog(
        user_id=user_id,
        logged_at=body.logged_at or datetime.utcnow(),
        meal_type=body.meal_type,
        food_name=body.food_name,
        quantity_grams=body.quantity_grams,
        calories=body.calories,
        protein_g=body.protein_g,
        carbs_g=body.carbs_g,
        fat_g=body.fat_g,
        source=body.source,
        barcode=body.barcode,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/logs", response_model=List[FoodLogResponse])
async def get_food_logs(
    date_str: str = Query(..., alias="date", description="Data in formato YYYY-MM-DD"),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato data non valido. Usa YYYY-MM-DD")

    start = datetime(target_date.year, target_date.month, target_date.day)
    end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)

    result = await db.execute(
        select(FoodLog)
        .where(
            FoodLog.user_id == user_id,
            FoodLog.logged_at >= start,
            FoodLog.logged_at <= end,
        )
        .order_by(FoodLog.logged_at)
    )
    return result.scalars().all()


@router.delete("/logs/{log_id}", status_code=204)
async def delete_food_log(
    log_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(FoodLog).where(FoodLog.id == log_id, FoodLog.user_id == user_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Log non trovato")
    await db.delete(log)
    await db.commit()


@router.post("/logs/photo")
async def analyze_food_photo(
    body: FoodPhotoRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Valida base64
    try:
        image_bytes = base64.b64decode(body.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Immagine base64 non valida")

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Immagine troppo grande (max 5MB)")

    # Valida formato (JPEG o PNG)
    is_jpeg = image_bytes[:3] == b"\xff\xd8\xff"
    is_png = image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    if not (is_jpeg or is_png):
        raise HTTPException(status_code=400, detail="Formato non supportato (solo JPEG/PNG)")

    # Upload su Supabase Storage
    user_id = uuid.UUID(current_user["user_id"])
    supabase = get_supabase()
    ext = "jpg" if is_jpeg else "png"
    storage_path = f"food-photos/{user_id}/{uuid.uuid4()}.{ext}"
    content_type = "image/jpeg" if is_jpeg else "image/png"

    try:
        supabase.storage.from_("food-photos").upload(
            storage_path,
            image_bytes,
            {"content-type": content_type},
        )
        photo_url = supabase.storage.from_("food-photos").get_public_url(storage_path)
    except Exception:
        photo_url = None

    # Analisi Claude Vision
    recognized = await claude_service.analyze_food_photo(body.image_base64, body.meal_type)
    if not recognized:
        raise HTTPException(status_code=422, detail="Impossibile riconoscere alimenti nell'immagine")

    return {
        "recognized_foods": recognized,
        "photo_url": photo_url,
        "meal_type": body.meal_type,
    }


# ── Dashboard Nutrizionale ─────────────────────────────────────────────────────

@router.get("/summary")
async def nutrition_summary(
    date_str: str = Query(..., alias="date"),
    calories_burned_healthkit: float = Query(0, description="Calorie bruciate da HealthKit"),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato data non valido. Usa YYYY-MM-DD")

    start = datetime(target_date.year, target_date.month, target_date.day)
    end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59)

    # Food logs del giorno
    logs_result = await db.execute(
        select(FoodLog)
        .where(FoodLog.user_id == user_id, FoodLog.logged_at >= start, FoodLog.logged_at <= end)
        .order_by(FoodLog.logged_at)
    )
    logs = logs_result.scalars().all()

    total_calories = sum(l.calories for l in logs)
    total_protein = sum(l.protein_g or 0 for l in logs)
    total_carbs = sum(l.carbs_g or 0 for l in logs)
    total_fat = sum(l.fat_g or 0 for l in logs)

    # Acqua del giorno
    water_result = await db.execute(
        select(func.sum(WaterLog.amount_ml)).where(
            WaterLog.user_id == user_id, WaterLog.logged_at >= start, WaterLog.logged_at <= end
        )
    )
    water_ml = water_result.scalar() or 0

    # Target calorico
    user = await _get_user(user_id, db)
    base_target = user.tdee or 2000.0
    target_calories = base_target + calories_burned_healthkit

    # Raggruppa per pasto
    logs_by_meal: Dict[str, list] = {}
    for log in logs:
        meal = log.meal_type
        if meal not in logs_by_meal:
            logs_by_meal[meal] = []
        logs_by_meal[meal].append(FoodLogResponse.model_validate(log))

    target_percentage = round((total_calories / target_calories * 100) if target_calories else 0, 1)

    return NutritionSummaryResponse(
        date=date_str,
        total_calories=round(total_calories, 1),
        protein_g=round(total_protein, 1),
        carbs_g=round(total_carbs, 1),
        fat_g=round(total_fat, 1),
        target_calories=round(target_calories, 1),
        target_percentage=target_percentage,
        water_ml=int(water_ml),
        logs_by_meal=logs_by_meal,
    )


@router.post("/water", status_code=201)
async def log_water(
    body: WaterLogCreate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    water = WaterLog(
        user_id=user_id,
        logged_at=body.logged_at or datetime.utcnow(),
        amount_ml=body.amount_ml,
    )
    db.add(water)
    await db.commit()
    await db.refresh(water)
    return {"id": str(water.id), "amount_ml": water.amount_ml, "logged_at": water.logged_at}


# ── Piano Dieta AI ─────────────────────────────────────────────────────────────

@router.post("/diet-plan/generate", response_model=DietPlanResponse, status_code=201)
async def generate_diet_plan(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    user = await _get_user(user_id, db)

    user_profile = {
        "name": user.name,
        "age": user.age,
        "weight_kg": user.weight_kg,
        "goals": user.goals,
        "fitness_level": user.fitness_level,
        "bmr": user.bmr,
        "tdee": user.tdee,
    }
    training_days = user.available_days or []
    plan_data = await claude_service.generate_diet_plan(user_profile, training_days)

    from datetime import timedelta
    today = datetime.utcnow()
    week_start = today - timedelta(days=today.weekday())

    plan = DietPlan(
        user_id=user_id,
        week_start_date=week_start,
        plan_json=plan_data,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/diet-plan/current", response_model=DietPlanResponse)
async def get_current_diet_plan(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    user_id = uuid.UUID(current_user["user_id"])
    today = datetime.utcnow()
    week_start = today - timedelta(days=today.weekday())

    result = await db.execute(
        select(DietPlan)
        .where(DietPlan.user_id == user_id, DietPlan.week_start_date >= week_start)
        .order_by(desc(DietPlan.generated_at))
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Nessun piano dieta per questa settimana")
    return plan


@router.post("/diet-plan/regenerate-day")
async def regenerate_diet_day(
    body: RegenerateDayRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    user_id = uuid.UUID(current_user["user_id"])
    today = datetime.utcnow()
    week_start = today - timedelta(days=today.weekday())

    result = await db.execute(
        select(DietPlan)
        .where(DietPlan.user_id == user_id, DietPlan.week_start_date >= week_start)
        .order_by(desc(DietPlan.generated_at))
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Nessun piano dieta trovato")

    user = await _get_user(user_id, db)
    user_profile = {
        "name": user.name,
        "goals": user.goals,
        "fitness_level": user.fitness_level,
        "bmr": user.bmr,
        "tdee": user.tdee,
        "available_days": user.available_days,
    }
    is_training = body.day.lower() in [d.lower() for d in (user.available_days or [])]

    new_day_plan = await claude_service.generate_diet_plan(
        user_profile, user.available_days or []
    )

    # Aggiorna solo il giorno richiesto nel piano esistente
    updated_json = dict(plan.plan_json)
    if "days" in new_day_plan and body.day in new_day_plan["days"]:
        updated_json.setdefault("days", {})[body.day] = new_day_plan["days"][body.day]
    plan.plan_json = updated_json
    await db.commit()
    await db.refresh(plan)

    return {"message": f"Giorno {body.day} rigenerato", "plan": DietPlanResponse.model_validate(plan)}


# ── Insights AI ────────────────────────────────────────────────────────────────

@router.post("/insights/generate", status_code=201)
async def generate_insights(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    user = await _get_user(user_id, db)

    today = datetime.utcnow()
    start = datetime(today.year, today.month, today.day)
    end = datetime(today.year, today.month, today.day, 23, 59, 59)

    logs_result = await db.execute(
        select(FoodLog).where(
            FoodLog.user_id == user_id, FoodLog.logged_at >= start, FoodLog.logged_at <= end
        )
    )
    logs = logs_result.scalars().all()
    logs_data = [
        {
            "food_name": l.food_name,
            "meal_type": l.meal_type,
            "calories": l.calories,
            "protein_g": l.protein_g,
            "carbs_g": l.carbs_g,
            "fat_g": l.fat_g,
        }
        for l in logs
    ]

    totals = {
        "calories": sum(l.calories for l in logs),
        "protein_g": sum(l.protein_g or 0 for l in logs),
        "carbs_g": sum(l.carbs_g or 0 for l in logs),
        "fat_g": sum(l.fat_g or 0 for l in logs),
    }

    # Cerca workout di oggi
    session_result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.started_at >= start,
            WorkoutSession.started_at <= end,
        ).limit(1)
    )
    session = session_result.scalar_one_or_none()
    workout_today = (
        {"calories_burned": session.calories_burned, "duration_minutes": session.duration_minutes}
        if session else None
    )

    user_profile = {
        "goals": user.goals,
        "bmr": user.bmr,
        "tdee": user.tdee,
    }

    raw_insights = await claude_service.generate_nutrition_insights(
        logs_data, totals, workout_today, user_profile
    )

    created = []
    for ins in raw_insights:
        insight = NutritionInsight(
            user_id=user_id,
            insight_text=ins.get("insight_text", ""),
            insight_type=ins.get("insight_type", "tip"),
        )
        db.add(insight)
        created.append(insight)

    await db.commit()
    for ins in created:
        await db.refresh(ins)

    return {"insights": [InsightResponse.model_validate(i) for i in created]}


@router.get("/insights", response_model=List[InsightResponse])
async def get_insights(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    user_id = uuid.UUID(current_user["user_id"])
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(NutritionInsight)
        .where(
            NutritionInsight.user_id == user_id,
            NutritionInsight.created_at >= seven_days_ago,
        )
        .order_by(desc(NutritionInsight.created_at))
    )
    return result.scalars().all()


@router.put("/insights/{insight_id}/read", response_model=InsightResponse)
async def mark_insight_read(
    insight_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(NutritionInsight).where(
            NutritionInsight.id == insight_id, NutritionInsight.user_id == user_id
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight non trovato")
    insight.read = True
    await db.commit()
    await db.refresh(insight)
    return insight
