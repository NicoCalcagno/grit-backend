from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def get_supabase():
    return create_client(settings.supabase_url, settings.supabase_service_key)


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    supabase = get_supabase()
    try:
        result = supabase.auth.admin.create_user(
            {"email": body.email, "password": body.password, "email_confirm": True}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    user_id = result.user.id
    db_user = User(
        id=user_id,
        name=body.name,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(db_user)
    await db.commit()

    try:
        login_result = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        session = login_result.session
        return {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user_id,
        }
    except Exception:
        return {"user_id": user_id, "message": "Utente creato. Effettua il login."}


@router.post("/login")
async def login(body: LoginRequest):
    supabase = get_supabase()
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    session = result.session
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
        "user_id": result.user.id,
    }


@router.post("/refresh")
async def refresh(body: RefreshRequest):
    supabase = get_supabase()
    try:
        result = supabase.auth.refresh_session(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token non valido o scaduto")

    session = result.session
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
    }


@router.post("/logout")
async def logout(current_user: Dict = Depends(get_current_user)):
    return {"message": "Logout effettuato"}
