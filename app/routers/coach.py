import time
import uuid
from collections import defaultdict
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.coach import (
    CoachMessageRequest,
    CoachMessageResponse,
    VoiceResponseRequest,
    VoiceResponseResponse,
    PlanModification,
)
from app.services import claude_service

router = APIRouter(prefix="/coach", tags=["coach"])

# Rate limiting: {user_id: [timestamps]}
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW = 60  # secondi


def _check_rate_limit(user_id: str):
    now = time.time()
    timestamps = _rate_limit_store[user_id]
    # Rimuovi timestamp fuori finestra
    _rate_limit_store[user_id] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[user_id]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Limite richieste superato. Max {RATE_LIMIT_MAX} richieste al minuto.",
        )
    _rate_limit_store[user_id].append(now)


async def _get_user_profile(user_id: uuid.UUID, db: AsyncSession) -> Dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"coach_tone": "motivating", "coach_language": "it", "name": ""}
    return {
        "name": user.name or "",
        "coach_tone": user.coach_tone or "motivating",
        "coach_language": user.coach_language or "it",
    }


@router.post("/message", response_model=CoachMessageResponse)
async def coach_message(
    body: CoachMessageRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id_str = current_user["user_id"]
    _check_rate_limit(user_id_str)

    user_profile = await _get_user_profile(uuid.UUID(user_id_str), db)

    session_context = body.session_context or {}
    session_context.update({
        "exercise_name": body.exercise_name,
        "set_number": body.set_number,
        "rep_count": body.rep_count,
        "heart_rate": body.heart_rate,
        "perceived_exertion": body.perceived_exertion,
        "elapsed_minutes": body.elapsed_minutes,
        "last_user_input": body.last_user_input,
    })

    text = await claude_service.generate_coach_message(body.event, session_context, user_profile)
    return CoachMessageResponse(text=text, event=body.event)


@router.post("/voice-response", response_model=VoiceResponseResponse)
async def voice_response(
    body: VoiceResponseRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id_str = current_user["user_id"]
    user_profile = await _get_user_profile(uuid.UUID(user_id_str), db)

    session_context = body.session_context or {}
    session_context.update({
        "exercise_name": body.exercise_name,
        "set_number": body.set_number,
        "rep_count": body.rep_count,
        "heart_rate": body.heart_rate,
        "perceived_exertion": body.perceived_exertion,
        "elapsed_minutes": body.elapsed_minutes,
    })

    result = await claude_service.generate_voice_response(
        body.transcribed_text, session_context, user_profile
    )

    modifications = [
        PlanModification(**m) for m in result.get("modifications", [])
    ]
    return VoiceResponseResponse(text=result.get("text", ""), modifications=modifications)
