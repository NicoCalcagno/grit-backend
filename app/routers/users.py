import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.health_service import compute_user_metrics

router = APIRouter(prefix="/users", tags=["users"])


def get_supabase():
    return create_client(settings.supabase_url, settings.supabase_service_key)


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    update_data = body.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    # Ricalcola BMR e TDEE se necessario
    metrics_fields = {"weight_kg", "height_cm", "age", "gender", "fitness_level"}
    if metrics_fields & set(update_data.keys()):
        bmr, tdee = compute_user_metrics(
            user.weight_kg,
            user.height_cm,
            user.age,
            user.gender,
            user.fitness_level,
        )
        user.bmr = bmr
        user.tdee = tdee

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/me", status_code=204)
async def delete_me(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.commit()

    supabase = get_supabase()
    try:
        supabase.auth.admin.delete_user(str(user_id))
    except Exception:
        pass
