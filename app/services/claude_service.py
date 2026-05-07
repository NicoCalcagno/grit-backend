import json
from typing import Any, Dict, List, Optional

import anthropic

from app.core.config import settings

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def generate_weekly_plan(
    user_profile: Dict[str, Any],
    recent_sessions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    prompt = f"""Sei un personal trainer AI. Genera un piano di allenamento settimanale personalizzato in JSON.

Profilo utente:
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

Ultime sessioni (contesto):
{json.dumps(recent_sessions, ensure_ascii=False, indent=2)}

Genera un piano JSON con questa struttura esatta:
{{
  "week_start": "YYYY-MM-DD",
  "days": {{
    "monday": {{
      "is_rest": false,
      "workout_type": "nome tipo allenamento",
      "warm_up": ["esercizio 1", "esercizio 2"],
      "exercises": [
        {{
          "name": "nome esercizio",
          "muscles": ["muscolo1", "muscolo2"],
          "sets": 3,
          "reps": "10-12",
          "rest_seconds": 60,
          "notes": "note opzionali"
        }}
      ],
      "cool_down": ["stretch 1", "stretch 2"],
      "ai_notes": "note personalizzate del coach"
    }},
    "tuesday": {{
      "is_rest": true,
      "rest_motivation": "Oggi riposa. Il recupero è parte dell'allenamento."
    }}
  }}
}}

Giorni disponibili dell'utente: {user_profile.get('available_days', [])}
Usa SOLO quei giorni per allenamenti, gli altri sono riposo.
Rispondi SOLO con il JSON, nessun testo aggiuntivo."""

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return _fallback_weekly_plan()


async def generate_session_summary(
    session_data: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> str:
    prompt = f"""Sei un personal trainer AI. Genera un breve riassunto motivazionale della sessione di allenamento.

Dati sessione:
{json.dumps(session_data, ensure_ascii=False, indent=2)}

Profilo utente:
- Nome: {user_profile.get('name', 'Atleta')}
- Tono coach: {user_profile.get('coach_tone', 'motivating')}
- Lingua: {user_profile.get('coach_language', 'it')}

Scrivi un riassunto di 2-3 frasi che:
1. Riconosca l'impegno dell'utente
2. Evidenzi i punti salienti della sessione
3. Motivi per la prossima volta

Rispondi direttamente con il testo, senza JSON."""

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return "Ottimo allenamento! Continua così, ogni sessione ti avvicina ai tuoi obiettivi."


async def generate_coach_message(
    event: str,
    session_context: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> str:
    tone = user_profile.get("coach_tone", "motivating")
    language = user_profile.get("coach_language", "it")
    name = user_profile.get("name", "")

    prompt = f"""Sei un personal trainer AI con tono {tone}.
Lingua di risposta: {language}
Nome utente: {name}

Evento corrente: {event}
Contesto sessione: {json.dumps(session_context, ensure_ascii=False)}

Genera UN messaggio breve (1-2 frasi max) da sintetizzare vocalmente durante l'allenamento.
Il messaggio deve essere appropriato all'evento e al contesto.
Rispondi SOLO con il testo del messaggio, niente altro."""

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return "Continua così, stai andando bene!"


async def generate_voice_response(
    transcribed_text: str,
    session_context: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> Dict[str, Any]:
    tone = user_profile.get("coach_tone", "motivating")
    language = user_profile.get("coach_language", "it")

    prompt = f"""Sei un personal trainer AI con tono {tone}.
Lingua: {language}
Contesto sessione: {json.dumps(session_context, ensure_ascii=False)}

L'utente ha detto (trascritto da voce): "{transcribed_text}"

Rispondi con un JSON con questa struttura:
{{
  "text": "tua risposta vocale (1-3 frasi)",
  "modifications": [
    {{
      "action": "reduce_sets|skip_exercise|change_weight|pause|none",
      "exercise_name": "nome esercizio se applicabile",
      "new_value": "nuovo valore se applicabile"
    }}
  ]
}}

Le modifications sono un array vuoto se non servono modifiche al piano.
Rispondi SOLO con il JSON."""

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return {"text": "Ho capito, continua come stai facendo!", "modifications": []}


async def analyze_food_photo(image_base64: str, meal_type: str) -> List[Dict[str, Any]]:
    prompt = """Analizza questa immagine di cibo e identifica tutti gli alimenti presenti.
Per ogni alimento, stima calorie e macronutrienti basandoti su una porzione tipica.

Rispondi con un JSON array:
[
  {
    "food_name": "nome alimento",
    "quantity_grams": 100,
    "calories": 200,
    "protein_g": 10,
    "carbs_g": 25,
    "fat_g": 8
  }
]

Sii preciso ma onesto sulle stime. Rispondi SOLO con il JSON array."""

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return []


async def generate_nutrition_insights(
    food_logs: List[Dict[str, Any]],
    totals: Dict[str, float],
    workout_today: Optional[Dict[str, Any]],
    user_profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    prompt = f"""Sei un nutrizionista AI. Analizza i dati nutrizionali dell'utente e genera 1-3 insights proattivi.

Profilo utente:
- Obiettivi: {user_profile.get('goals', [])}
- TDEE: {user_profile.get('tdee')} kcal
- BMR: {user_profile.get('bmr')} kcal

Log pasti di oggi:
{json.dumps(food_logs, ensure_ascii=False, indent=2)}

Totali del giorno:
{json.dumps(totals, ensure_ascii=False)}

Workout di oggi: {json.dumps(workout_today, ensure_ascii=False) if workout_today else "Nessuno"}

Genera insights utili in JSON array:
[
  {{
    "insight_text": "testo dell'insight",
    "insight_type": "warning|tip|positive"
  }}
]

- warning: attenzione (eccesso calorie, carenza proteica, ecc.)
- tip: consiglio pratico
- positive: rinforzo positivo quando l'utente ha fatto bene

Rispondi SOLO con il JSON array."""

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return [{"insight_text": "Continua a tracciare la tua alimentazione per ricevere consigli personalizzati.", "insight_type": "tip"}]


async def generate_diet_plan(
    user_profile: Dict[str, Any],
    training_days: List[str],
) -> Dict[str, Any]:
    prompt = f"""Sei un nutrizionista AI. Genera un piano alimentare settimanale personalizzato.

Profilo utente:
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

Giorni di allenamento: {training_days}

Target calorico:
- Giorni allenamento: {int((user_profile.get('tdee') or 2000) * 1.1)} kcal
- Giorni riposo: {int((user_profile.get('tdee') or 2000) * 0.9)} kcal

Genera piano JSON:
{{
  "days": {{
    "monday": {{
      "is_training_day": true,
      "target_calories": 2200,
      "meals": {{
        "breakfast": {{
          "description": "descrizione pasto",
          "foods": ["alimento 1", "alimento 2"],
          "calories": 400,
          "protein_g": 25,
          "carbs_g": 50,
          "fat_g": 12
        }},
        "lunch": {{ ... }},
        "dinner": {{ ... }},
        "snack": {{ ... }}
      }}
    }}
  }}
}}

Rispondi SOLO con il JSON."""

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except (json.JSONDecodeError, Exception):
        return {"days": {}}


async def generate_weekly_summary(
    workout_data: Dict[str, Any],
    nutrition_data: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> str:
    prompt = f"""Sei un personal trainer AI. Genera un riassunto settimanale per l'utente.

Dati workout settimana:
{json.dumps(workout_data, ensure_ascii=False, indent=2)}

Dati nutrizione settimana:
{json.dumps(nutrition_data, ensure_ascii=False, indent=2)}

Profilo utente:
- Nome: {user_profile.get('name', 'Atleta')}
- Obiettivi: {user_profile.get('goals', [])}
- Tono: {user_profile.get('coach_tone', 'motivating')}
- Lingua: {user_profile.get('coach_language', 'it')}

Scrivi un riassunto di 3-5 frasi che:
1. Valuti la settimana nel complesso
2. Evidenzi punti di forza
3. Suggerisca un'area di miglioramento
4. Motivi per la settimana successiva

Scrivi in modo personale e motivante. Solo testo, nessun JSON."""

    try:
        response = await client.messages.create(
            model=settings.claude_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return "Ottima settimana! Hai dimostrato dedizione e costanza. Continua su questa strada e i risultati arriveranno."


def _fallback_weekly_plan() -> Dict[str, Any]:
    return {
        "week_start": "",
        "days": {
            "monday": {"is_rest": False, "workout_type": "Full Body", "warm_up": [], "exercises": [], "cool_down": [], "ai_notes": ""},
            "tuesday": {"is_rest": True, "rest_motivation": "Recupero attivo."},
            "wednesday": {"is_rest": False, "workout_type": "Cardio", "warm_up": [], "exercises": [], "cool_down": [], "ai_notes": ""},
            "thursday": {"is_rest": True, "rest_motivation": "Riposo."},
            "friday": {"is_rest": False, "workout_type": "Full Body", "warm_up": [], "exercises": [], "cool_down": [], "ai_notes": ""},
            "saturday": {"is_rest": True, "rest_motivation": "Riposo."},
            "sunday": {"is_rest": True, "rest_motivation": "Riposo."},
        },
    }
