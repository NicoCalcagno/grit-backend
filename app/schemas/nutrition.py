from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class FoodLogCreate(BaseModel):
    logged_at: Optional[datetime] = None
    meal_type: str
    food_name: str
    quantity_grams: float
    calories: float
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    source: str = "manual"
    barcode: Optional[str] = None


class FoodLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    logged_at: datetime
    meal_type: str
    food_name: str
    quantity_grams: float
    calories: float
    protein_g: Optional[float]
    carbs_g: Optional[float]
    fat_g: Optional[float]
    source: str
    barcode: Optional[str]
    photo_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class FoodPhotoRequest(BaseModel):
    image_base64: str
    meal_type: str = "lunch"


class WaterLogCreate(BaseModel):
    logged_at: Optional[datetime] = None
    amount_ml: int = 250


class NutritionSummaryResponse(BaseModel):
    date: str
    total_calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    target_calories: float
    target_percentage: float
    water_ml: int
    logs_by_meal: Dict[str, List[FoodLogResponse]]


class InsightResponse(BaseModel):
    id: UUID
    user_id: UUID
    generated_at: datetime
    insight_text: str
    insight_type: str
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DietPlanResponse(BaseModel):
    id: UUID
    user_id: UUID
    week_start_date: datetime
    plan_json: Dict[str, Any]
    generated_at: datetime

    model_config = {"from_attributes": True}


class RegenerateDayRequest(BaseModel):
    day: str  # es. "monday", "tuesday", ecc.
