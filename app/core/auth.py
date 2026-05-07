import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings

security = HTTPBearer()

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=5.0)
            resp.raise_for_status()
            _jwks_cache = resp.json()
    return _jwks_cache


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg", "ES256")

        if alg == "HS256":
            # Fallback per token legacy Supabase (HS256 shared secret)
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        else:
            jwks = await _get_jwks()
            key = next(
                (k for k in jwks.get("keys", []) if k.get("kid") == kid),
                jwks["keys"][0] if jwks.get("keys") else None,
            )
            if key is None:
                raise JWTError("Nessuna chiave JWT trovata")
            payload = jwt.decode(
                token,
                key,
                algorithms=[alg],
                options={"verify_aud": False},
            )

        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token non valido")
        return {"user_id": user_id, "payload": payload}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token non valido o scaduto")
