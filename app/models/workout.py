import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start_date = Column(DateTime, nullable=False)
    plan_json = Column(JSONB, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("weekly_plans.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    calories_burned = Column(Float, nullable=True)
    avg_heart_rate = Column(Integer, nullable=True)
    perceived_exertion = Column(Integer, nullable=True)
    exercises_completed = Column(JSONB, nullable=True)
    exercises_skipped = Column(JSONB, nullable=True)
    ai_summary = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
