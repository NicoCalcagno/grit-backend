import uuid
from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.nutrition import FoodLog
from app.models.user import User
from app.models.workout import WorkoutSession
from app.services import claude_service

router = APIRouter(prefix="/progress", tags=["progress"])


async def _get_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.get("/workouts")
async def workout_progress(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])

    # Sessioni completate ultima settimana
    week_ago = datetime.utcnow() - timedelta(days=7)

    result = await db.execute(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.completed_at.isnot(None),
        )
        .order_by(desc(WorkoutSession.completed_at))
    )
    all_sessions = result.scalars().all()

    # Calorie per settimana (ultime 4)
    calories_by_week: Dict[str, float] = {}
    for s in all_sessions:
        if s.completed_at and s.calories_burned:
            week_label = s.completed_at.strftime("%Y-W%W")
            calories_by_week[week_label] = calories_by_week.get(week_label, 0) + s.calories_burned

    # FC media per sessione (ultime 10)
    recent_hr = [
        {"session_id": str(s.id), "avg_heart_rate": s.avg_heart_rate, "date": str(s.completed_at)}
        for s in all_sessions[:10]
        if s.avg_heart_rate
    ]

    # Streak: giorni consecutivi con sessione completata
    completed_dates = sorted(
        {s.completed_at.date() for s in all_sessions if s.completed_at}, reverse=True
    )
    streak = 0
    if completed_dates:
        today = datetime.utcnow().date()
        expected = today
        for d in completed_dates:
            if d == expected or d == expected - timedelta(days=1):
                streak += 1
                expected = d - timedelta(days=1)
            else:
                break

    week_sessions = [s for s in all_sessions if s.completed_at and s.completed_at >= week_ago]
    total_sessions = len(all_sessions)
    total_minutes = sum(s.duration_minutes or 0 for s in all_sessions)

    return {
        "calories_by_week": calories_by_week,
        "heart_rate_by_session": recent_hr,
        "streak_days": streak,
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "sessions_this_week": len(week_sessions),
        "calories_this_week": sum(s.calories_burned or 0 for s in week_sessions),
    }


@router.get("/nutrition")
async def nutrition_progress(
    days: int = Query(7, ge=7, le=30),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(FoodLog)
        .where(FoodLog.user_id == user_id, FoodLog.logged_at >= since)
        .order_by(FoodLog.logged_at)
    )
    logs = result.scalars().all()

    user = await _get_user(user_id, db)
    target_calories = user.tdee or 2000.0 if user else 2000.0

    # Aggrega per giorno
    by_day: Dict[str, Dict] = {}
    for log in logs:
        day_key = log.logged_at.strftime("%Y-%m-%d")
        if day_key not in by_day:
            by_day[day_key] = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
        by_day[day_key]["calories"] += log.calories
        by_day[day_key]["protein_g"] += log.protein_g or 0
        by_day[day_key]["carbs_g"] += log.carbs_g or 0
        by_day[day_key]["fat_g"] += log.fat_g or 0

    days_tracked = len(by_day)
    avg_calories = (sum(d["calories"] for d in by_day.values()) / days_tracked) if days_tracked else 0
    days_on_target = sum(1 for d in by_day.values() if abs(d["calories"] - target_calories) <= target_calories * 0.1)

    # Trend macros settimanale
    weekly_macros: Dict[str, Dict] = {}
    for log in logs:
        week_label = log.logged_at.strftime("%Y-W%W")
        if week_label not in weekly_macros:
            weekly_macros[week_label] = {"protein_g": 0, "carbs_g": 0, "fat_g": 0}
        weekly_macros[week_label]["protein_g"] += log.protein_g or 0
        weekly_macros[week_label]["carbs_g"] += log.carbs_g or 0
        weekly_macros[week_label]["fat_g"] += log.fat_g or 0

    return {
        "period_days": days,
        "avg_daily_calories": round(avg_calories, 1),
        "days_on_target": days_on_target,
        "days_tracked": days_tracked,
        "target_calories": target_calories,
        "daily_breakdown": by_day,
        "weekly_macros": weekly_macros,
    }


@router.get("/weekly-summary")
async def weekly_summary(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    week_ago = datetime.utcnow() - timedelta(days=7)

    # Dati workout
    sessions_result = await db.execute(
        select(WorkoutSession)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.completed_at >= week_ago,
            WorkoutSession.completed_at.isnot(None),
        )
    )
    sessions = sessions_result.scalars().all()
    workout_data = {
        "total_sessions": len(sessions),
        "total_minutes": sum(s.duration_minutes or 0 for s in sessions),
        "total_calories_burned": sum(s.calories_burned or 0 for s in sessions),
        "avg_perceived_exertion": (
            sum(s.perceived_exertion or 0 for s in sessions) / len(sessions) if sessions else 0
        ),
    }

    # Dati nutrizione
    logs_result = await db.execute(
        select(FoodLog).where(FoodLog.user_id == user_id, FoodLog.logged_at >= week_ago)
    )
    logs = logs_result.scalars().all()
    nutrition_data = {
        "total_calories_logged": sum(log.calories for log in logs),
        "avg_daily_calories": round(sum(log.calories for log in logs) / 7, 1),
        "total_protein_g": sum(log.protein_g or 0 for log in logs),
        "days_logged": len({log.logged_at.date() for log in logs}),
    }

    # Profilo utente
    user = await _get_user(user_id, db)
    user_profile = {
        "name": user.name if user else "",
        "goals": user.goals if user else [],
        "coach_tone": user.coach_tone if user else "motivating",
        "coach_language": user.coach_language if user else "it",
    }

    summary_text = await claude_service.generate_weekly_summary(
        workout_data, nutrition_data, user_profile
    )

    return {
        "summary": summary_text,
        "workout_stats": workout_data,
        "nutrition_stats": nutrition_data,
    }
