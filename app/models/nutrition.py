import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class FoodLog(Base):
    __tablename__ = "food_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    logged_at = Column(DateTime, nullable=False)
    meal_type = Column(String, nullable=False)  # breakfast/lunch/dinner/snack
    food_name = Column(String, nullable=False)
    quantity_grams = Column(Float, nullable=False)
    calories = Column(Float, nullable=False)
    protein_g = Column(Float, nullable=True)
    carbs_g = Column(Float, nullable=True)
    fat_g = Column(Float, nullable=True)
    source = Column(String, nullable=False)  # barcode/photo/manual
    barcode = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NutritionInsight(Base):
    __tablename__ = "nutrition_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    insight_text = Column(String, nullable=False)
    insight_type = Column(String, nullable=False)  # warning/tip/positive
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DietPlan(Base):
    __tablename__ = "diet_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    week_start_date = Column(DateTime, nullable=False)
    plan_json = Column(JSONB, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)


class WaterLog(Base):
    __tablename__ = "water_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    logged_at = Column(DateTime, nullable=False)
    amount_ml = Column(Integer, nullable=False, default=250)
    created_at = Column(DateTime, default=datetime.utcnow)
