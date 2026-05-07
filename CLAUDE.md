# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandi principali

```bash
# Avvia server di sviluppo
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Installa dipendenze
pip install -r requirements.txt

# Copia variabili d'ambiente
cp .env.example .env
```

Non ci sono test automatici configurati al momento.

## Architettura

Backend FastAPI per l'app iOS **Grit** (personal trainer AI). Il client iOS non chiama mai direttamente Claude, Spotify o Open Food Facts — tutto passa da questo backend.

**Stack:** FastAPI + SQLAlchemy async (asyncpg) + Supabase (PostgreSQL + Auth + Storage) + Anthropic Claude API + Spotify Web API + Open Food Facts.

### Struttura dei layer

```
app/
├── core/        # config, database, auth middleware
├── routers/     # endpoint HTTP (un file per dominio)
├── models/      # SQLAlchemy ORM models
├── schemas/     # Pydantic v2 request/response schemas
└── services/    # wrapper per servizi esterni (Claude, Spotify, food)
```

### Autenticazione

`app/core/auth.py` espone `get_current_user` come dipendenza FastAPI. Decodifica il JWT Supabase (HS256, `jwt_secret`) e restituisce `{"user_id": str, "payload": dict}`. Tutti gli endpoint protetti usano `Depends(get_current_user)`.

### Integrazione Claude

`app/services/claude_service.py` contiene tutte le chiamate all'API Anthropic. Il modello usato è configurabile via `CLAUDE_MODEL` (default `claude-sonnet-4-20250514`). Le risposte JSON di Claude vanno sempre parsate in try/except — ogni funzione ha un fallback strutturato in caso di errore o JSON non valido.

### Database

SQLAlchemy async con `asyncpg`. La sessione è iniettata via `Depends(get_db)` (generatore async in `app/core/database.py`). Il `DATABASE_URL` deve usare il prefisso `postgresql+asyncpg://`.

### Rate limiting del coach

`app/routers/coach.py` implementa rate limiting in memoria: `{user_id: [timestamps]}` con massimo 3 richieste/minuto per utente. Non è persistente al riavvio.

## Variabili d'ambiente richieste

```
ANTHROPIC_API_KEY
SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET
SPOTIFY_REDIRECT_URI
SUPABASE_URL
SUPABASE_SERVICE_KEY
JWT_SECRET
DATABASE_URL        # postgresql+asyncpg://...
CLAUDE_MODEL        # opzionale, default claude-sonnet-4-20250514
```

## Schema database

Le tabelle principali in Supabase/PostgreSQL sono: `users` (profilo fitness, estende Supabase Auth), `weekly_plans` (piano settimanale AI in JSONB), `workout_sessions`, `food_logs`, `nutrition_insights`, `diet_plans`, `spotify_tokens`.

Il campo `plan_json` di `weekly_plans` e `diet_plans` è JSONB — la struttura esatta è definita nei prompt in `claude_service.py`.

## Deploy

Hosting su Railway. Il `Procfile` avvia uvicorn sulla porta `$PORT`.
