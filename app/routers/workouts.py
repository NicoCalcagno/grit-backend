import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.workout import WeeklyPlan, WorkoutSession
from app.schemas.workout import (
    SessionComplete,
    SessionCreate,
    SessionResponse,
    SessionUpdate,
    WeeklyPlanResponse,
)
from app.services import claude_service

router = APIRouter(prefix="/workouts", tags=["workouts"])


def _week_start(dt: datetime) -> datetime:
    """Restituisce il lunedì della settimana corrente."""
    return dt - timedelta(days=dt.weekday())


async def _get_user(user_id: uuid.UUID, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return user


# ── Piano settimanale ──────────────────────────────────────────────────────────

@router.post("/weekly-plan/generate", response_model=WeeklyPlanResponse, status_code=201)
async def generate_weekly_plan(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    user = await _get_user(user_id, db)

    recent_q = await db.execute(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id, WorkoutSession.completed_at.isnot(None))
        .order_by(desc(WorkoutSession.completed_at))
        .limit(5)
    )
    recent_sessions = [
        {
            "started_at": str(s.started_at),
            "duration_minutes": s.duration_minutes,
            "calories_burned": s.calories_burned,
            "perceived_exertion": s.perceived_exertion,
        }
        for s in recent_q.scalars().all()
    ]

    user_profile = {
        "name": user.name,
        "age": user.age,
        "weight_kg": user.weight_kg,
        "height_cm": user.height_cm,
        "gender": user.gender,
        "fitness_level": user.fitness_level,
        "goals": user.goals,
        "available_days": user.available_days,
        "preferred_workouts": user.preferred_workouts,
        "bmr": user.bmr,
        "tdee": user.tdee,
    }

    plan_data = await claude_service.generate_weekly_plan(user_profile, recent_sessions)
    week_start = _week_start(datetime.utcnow())

    plan = WeeklyPlan(
        user_id=user_id,
        week_start_date=week_start,
        plan_json=plan_data,
        generated_at=datetime.utcnow(),
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.get("/weekly-plan/current", response_model=WeeklyPlanResponse)
async def get_current_plan(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    week_start = _week_start(datetime.utcnow())

    result = await db.execute(
        select(WeeklyPlan)
        .where(WeeklyPlan.user_id == user_id, WeeklyPlan.week_start_date >= week_start)
        .order_by(desc(WeeklyPlan.generated_at))
        .limit(1)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Nessun piano per questa settimana")
    return plan


@router.post("/weekly-plan/regenerate", response_model=WeeklyPlanResponse, status_code=201)
async def regenerate_weekly_plan(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await generate_weekly_plan(current_user=current_user, db=db)


# ── Sessioni workout ───────────────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    session = WorkoutSession(
        user_id=user_id,
        plan_id=body.plan_id,
        started_at=body.started_at or datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.put("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id, WorkoutSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessione non trovata")

    for key, value in body.model_dump(exclude_none=True).items():
        setattr(session, key, value)

    await db.commit()
    await db.refresh(session)
    return session


@router.post("/sessions/{session_id}/complete", response_model=SessionResponse)
async def complete_session(
    session_id: uuid.UUID,
    body: SessionComplete,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id, WorkoutSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessione non trovata")

    for key, value in body.model_dump(exclude_none=True).items():
        setattr(session, key, value)

    session.completed_at = body.completed_at or datetime.utcnow()
    if not session.duration_minutes and session.started_at:
        delta = session.completed_at - session.started_at
        session.duration_minutes = int(delta.total_seconds() / 60)

    # Recupera profilo per il summary
    user = await _get_user(user_id, db)
    user_profile = {"name": user.name, "coach_tone": user.coach_tone, "coach_language": user.coach_language}
    session_data = {
        "duration_minutes": session.duration_minutes,
        "calories_burned": session.calories_burned,
        "avg_heart_rate": session.avg_heart_rate,
        "perceived_exertion": session.perceived_exertion,
        "exercises_completed": session.exercises_completed,
        "exercises_skipped": session.exercises_skipped,
    }
    session.ai_summary = await claude_service.generate_session_summary(session_data, user_profile)

    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    user_id = uuid.UUID(current_user["user_id"])
    offset = (page - 1) * page_size
    result = await db.execute(
        select(WorkoutSession)
        .where(WorkoutSession.user_id == user_id)
        .order_by(desc(WorkoutSession.started_at))
        .offset(offset)
        .limit(page_size)
    )
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(
        select(WorkoutSession).where(
            WorkoutSession.id == session_id, WorkoutSession.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessione non trovata")
    return session
