import base64
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import httpx

from app.core.config import settings

SPOTIFY_AUTH_URL = "https://accounts.spotify.com"
SPOTIFY_API_URL = "https://api.spotify.com/v1"

SCOPES = "user-read-playback-state user-modify-playback-state playlist-read-private streaming"

PHASE_PARAMS = {
    "warmup": {"min_tempo": 90, "max_tempo": 120, "target_energy": 0.5, "target_valence": 0.6},
    "peak": {"min_tempo": 130, "max_tempo": 180, "target_energy": 0.9, "target_valence": 0.8},
    "recovery": {"min_tempo": 70, "max_tempo": 100, "target_energy": 0.3, "target_valence": 0.4},
    "cooldown": {"min_tempo": 60, "max_tempo": 90, "target_energy": 0.2, "target_valence": 0.3},
}


def get_auth_url(state: str = "") -> str:
    params = {
        "client_id": settings.spotify_client_id,
        "response_type": "code",
        "redirect_uri": settings.spotify_redirect_uri,
        "scope": SCOPES,
        "state": state,
    }
    return f"{SPOTIFY_AUTH_URL}/authorize?{urlencode(params)}"


async def exchange_code(code: str) -> Dict[str, Any]:
    credentials = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SPOTIFY_AUTH_URL}/api/token",
            headers={"Authorization": f"Basic {credentials}"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": expires_at,
    }


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    credentials = base64.b64encode(
        f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SPOTIFY_AUTH_URL}/api/token",
            headers={"Authorization": f"Basic {credentials}"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])
    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),
        "expires_at": expires_at,
    }


async def get_recommendations(
    access_token: str,
    phase: str,
    perceived_exertion: int = 5,
    limit: int = 10,
) -> List[Dict]:
    params_base = PHASE_PARAMS.get(phase, PHASE_PARAMS["peak"])

    energy_boost = min(0.1, (perceived_exertion - 5) * 0.02)
    target_energy = min(1.0, params_base["target_energy"] + energy_boost)

    params = {
        "limit": limit,
        "seed_genres": "workout,pop,hip-hop",
        "min_tempo": params_base["min_tempo"],
        "max_tempo": params_base["max_tempo"],
        "target_energy": target_energy,
        "target_valence": params_base["target_valence"],
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_URL}/recommendations",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

    tracks = []
    for item in data.get("tracks", []):
        tracks.append({
            "id": item["id"],
            "name": item["name"],
            "artists": [a["name"] for a in item.get("artists", [])],
            "album": item.get("album", {}).get("name", ""),
            "preview_url": item.get("preview_url"),
            "external_url": item.get("external_urls", {}).get("spotify", ""),
            "duration_ms": item.get("duration_ms", 0),
        })
    return tracks
