from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CoachMessageRequest(BaseModel):
    event: str  # exercise_start, mid_set, rest_start, ecc.
    exercise_name: Optional[str] = None
    set_number: Optional[int] = None
    rep_count: Optional[int] = None
    heart_rate: Optional[int] = None
    perceived_exertion: Optional[int] = None
    elapsed_minutes: Optional[int] = None
    last_user_input: Optional[str] = None
    session_context: Optional[Dict[str, Any]] = None


class CoachMessageResponse(BaseModel):
    text: str
    event: str


class VoiceResponseRequest(BaseModel):
    transcribed_text: str
    exercise_name: Optional[str] = None
    set_number: Optional[int] = None
    rep_count: Optional[int] = None
    heart_rate: Optional[int] = None
    perceived_exertion: Optional[int] = None
    elapsed_minutes: Optional[int] = None
    session_context: Optional[Dict[str, Any]] = None


class PlanModification(BaseModel):
    action: str  # reduce_sets, skip_exercise, change_weight, ecc.
    exercise_name: Optional[str] = None
    new_value: Optional[Any] = None


class VoiceResponseResponse(BaseModel):
    text: str
    modifications: List[PlanModification] = []
