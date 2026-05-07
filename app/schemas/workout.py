from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class SessionCreate(BaseModel):
    plan_id: Optional[UUID] = None
    started_at: Optional[datetime] = None


class SessionUpdate(BaseModel):
    calories_burned: Optional[float] = None
    avg_heart_rate: Optional[int] = None
    perceived_exertion: Optional[int] = None
    exercises_completed: Optional[List[Dict[str, Any]]] = None
    exercises_skipped: Optional[List[Dict[str, Any]]] = None


class SessionComplete(BaseModel):
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    avg_heart_rate: Optional[int] = None
    perceived_exertion: Optional[int] = None
    exercises_completed: Optional[List[Dict[str, Any]]] = None
    exercises_skipped: Optional[List[Dict[str, Any]]] = None


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    plan_id: Optional[UUID]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_minutes: Optional[int]
    calories_burned: Optional[float]
    avg_heart_rate: Optional[int]
    perceived_exertion: Optional[int]
    exercises_completed: Optional[List[Dict[str, Any]]]
    exercises_skipped: Optional[List[Dict[str, Any]]]
    ai_summary: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class WeeklyPlanResponse(BaseModel):
    id: UUID
    user_id: UUID
    week_start_date: datetime
    plan_json: Dict[str, Any]
    generated_at: datetime

    model_config = {"from_attributes": True}
