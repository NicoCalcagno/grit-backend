import uuid
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.progress import SpotifyToken
from app.schemas.spotify import (
    SpotifyCallbackRequest,
    SpotifyRecommendationsResponse,
    SpotifyStatusResponse,
    SpotifyTrack,
)
from app.services import spotify_service

router = APIRouter(prefix="/spotify", tags=["spotify"])


async def _get_valid_token(user_id: uuid.UUID, db: AsyncSession) -> str:
    result = await db.execute(select(SpotifyToken).where(SpotifyToken.user_id == user_id))
    token_row = result.scalar_one_or_none()
    if not token_row:
        raise HTTPException(status_code=404, detail="Spotify non connesso")

    if token_row.expires_at <= datetime.utcnow():
        refreshed = await spotify_service.refresh_access_token(token_row.refresh_token)
        token_row.access_token = refreshed["access_token"]
        token_row.refresh_token = refreshed["refresh_token"]
        token_row.expires_at = refreshed["expires_at"]
        token_row.updated_at = datetime.utcnow()
        await db.commit()

    return token_row.access_token


@router.get("/auth-url")
async def get_auth_url(state: str = ""):
    url = spotify_service.get_auth_url(state)
    return {"auth_url": url}


@router.post("/callback")
async def spotify_callback(
    body: SpotifyCallbackRequest,
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    try:
        tokens = await spotify_service.exchange_code(body.code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Errore scambio token: {str(e)}")

    result = await db.execute(select(SpotifyToken).where(SpotifyToken.user_id == user_id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.access_token = tokens["access_token"]
        existing.refresh_token = tokens["refresh_token"]
        existing.expires_at = tokens["expires_at"]
        existing.updated_at = datetime.utcnow()
    else:
        db.add(SpotifyToken(
            user_id=user_id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_at=tokens["expires_at"],
            updated_at=datetime.utcnow(),
        ))

    await db.commit()
    return {"message": "Spotify connesso con successo"}


@router.post("/refresh")
async def refresh_spotify(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(select(SpotifyToken).where(SpotifyToken.user_id == user_id))
    token_row = result.scalar_one_or_none()
    if not token_row:
        raise HTTPException(status_code=404, detail="Spotify non connesso")

    try:
        refreshed = await spotify_service.refresh_access_token(token_row.refresh_token)
    except Exception:
        raise HTTPException(status_code=400, detail="Impossibile rinnovare il token Spotify")

    token_row.access_token = refreshed["access_token"]
    token_row.refresh_token = refreshed["refresh_token"]
    token_row.expires_at = refreshed["expires_at"]
    token_row.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "Token rinnovato", "expires_at": refreshed["expires_at"]}


@router.get("/recommendations", response_model=SpotifyRecommendationsResponse)
async def get_recommendations(
    phase: str = Query(..., pattern="^(warmup|peak|recovery|cooldown)$"),
    perceived_exertion: int = Query(5, ge=1, le=10),
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    access_token = await _get_valid_token(user_id, db)

    try:
        tracks_data = await spotify_service.get_recommendations(
            access_token, phase, perceived_exertion
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Errore Spotify: {str(e)}")

    tracks = [SpotifyTrack(**t) for t in tracks_data]
    return SpotifyRecommendationsResponse(phase=phase, tracks=tracks)


@router.get("/status", response_model=SpotifyStatusResponse)
async def spotify_status(
    current_user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current_user["user_id"])
    result = await db.execute(select(SpotifyToken).where(SpotifyToken.user_id == user_id))
    token_row = result.scalar_one_or_none()
    if not token_row:
        return SpotifyStatusResponse(connected=False)
    return SpotifyStatusResponse(connected=True, expires_at=token_row.expires_at)
