import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Float, nullable=True)
    gender = Column(String, nullable=True)
    fitness_level = Column(String, nullable=True)
    goals = Column(ARRAY(String), nullable=True)
    available_days = Column(ARRAY(String), nullable=True)
    preferred_workouts = Column(ARRAY(String), nullable=True)
    coach_language = Column(String, default="it")
    coach_tone = Column(String, default="motivating")
    onboarding_completed = Column(Boolean, default=False)
    bmr = Column(Float, nullable=True)
    tdee = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
