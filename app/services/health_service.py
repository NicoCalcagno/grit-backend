from typing import Optional


def calculate_bmr(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
) -> float:
    """Calcola il BMR con la formula di Mifflin-St Jeor."""
    if gender.lower() in ("male", "m", "uomo"):
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def calculate_tdee(bmr: float, fitness_level: str) -> float:
    """Calcola il TDEE applicando il moltiplicatore di attività."""
    multipliers = {
        "sedentary": 1.2,
        "beginner": 1.375,
        "intermediate": 1.55,
        "advanced": 1.725,
        "athlete": 1.9,
    }
    multiplier = multipliers.get(fitness_level.lower(), 1.375)
    return bmr * multiplier


def compute_user_metrics(
    weight_kg: Optional[float],
    height_cm: Optional[float],
    age: Optional[int],
    gender: Optional[str],
    fitness_level: Optional[str],
) -> tuple[Optional[float], Optional[float]]:
    """Restituisce (bmr, tdee) se i dati sono sufficienti, altrimenti (None, None)."""
    if not all([weight_kg, height_cm, age, gender, fitness_level]):
        return None, None
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, fitness_level)
    return round(bmr, 1), round(tdee, 1)
