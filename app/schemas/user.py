from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class UserUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    gender: Optional[str] = None
    fitness_level: Optional[str] = None
    goals: Optional[List[str]] = None
    available_days: Optional[List[str]] = None
    preferred_workouts: Optional[List[str]] = None
    coach_language: Optional[str] = None
    coach_tone: Optional[str] = None
    onboarding_completed: Optional[bool] = None


class UserResponse(BaseModel):
    id: UUID
    name: Optional[str]
    age: Optional[int]
    weight_kg: Optional[float]
    height_cm: Optional[float]
    gender: Optional[str]
    fitness_level: Optional[str]
    goals: Optional[List[str]]
    available_days: Optional[List[str]]
    preferred_workouts: Optional[List[str]]
    coach_language: Optional[str]
    coach_tone: Optional[str]
    onboarding_completed: bool
    bmr: Optional[float]
    tdee: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
