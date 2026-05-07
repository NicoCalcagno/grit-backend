from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class SpotifyCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


class SpotifyTrack(BaseModel):
    id: str
    name: str
    artists: List[str]
    album: str
    preview_url: Optional[str]
    external_url: str
    duration_ms: int
    tempo: Optional[float] = None
    energy: Optional[float] = None


class SpotifyRecommendationsResponse(BaseModel):
    phase: str
    tracks: List[SpotifyTrack]


class SpotifyStatusResponse(BaseModel):
    connected: bool
    expires_at: Optional[datetime] = None
