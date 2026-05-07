# Grit Backend

Backend REST API per **Grit**, l'app iOS di personal training AI. Fa da intermediario tra il client mobile e tutti i servizi esterni: l'app non chiama mai direttamente Claude, Spotify o Open Food Facts.

## Stack

| | |
|---|---|
| Framework | FastAPI (Python 3.12) |
| Database | Supabase (PostgreSQL) |
| ORM | SQLAlchemy async + asyncpg |
| Auth | Supabase Auth (JWT HS256) |
| Storage | Supabase Storage (foto piatti) |
| AI | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Musica | Spotify Web API |
| Alimenti | Open Food Facts API |
| Deploy | Railway |

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # compila le variabili
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Documentazione interattiva disponibile su `http://localhost:8000/docs`.

## Variabili d'ambiente

```
ANTHROPIC_API_KEY=
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=http://localhost:8000/spotify/callback
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
JWT_SECRET=
DATABASE_URL=postgresql+asyncpg://postgres:[password]@db.[project].supabase.co:5432/postgres
CLAUDE_MODEL=          # opzionale, default claude-sonnet-4-20250514
```

## API

Tutti gli endpoint (eccetto `/auth/*` e `/health`) richiedono il header:
```
Authorization: Bearer <jwt>
```

### Auth
| Metodo | Path | Descrizione |
|---|---|---|
| POST | `/auth/register` | Crea utente su Supabase Auth + profilo |
| POST | `/auth/login` | Restituisce access + refresh token |
| POST | `/auth/refresh` | Rinnova JWT |
| POST | `/auth/logout` | Logout |

### Utente
| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/users/me` | Profilo completo |
| PUT | `/users/me` | Aggiorna profilo (peso, obiettivi, preferenze coach, ecc.) |
| DELETE | `/users/me` | Cancella account e tutti i dati |

### Workout
| Metodo | Path | Descrizione |
|---|---|---|
| POST | `/workouts/weekly-plan/generate` | Genera piano settimanale via Claude |
| GET | `/workouts/weekly-plan/current` | Piano della settimana corrente |
| POST | `/workouts/weekly-plan/regenerate` | Rigenera il piano |
| POST | `/workouts/sessions` | Apre una nuova sessione |
| PUT | `/workouts/sessions/{id}` | Aggiorna sessione in corso |
| POST | `/workouts/sessions/{id}/complete` | Chiude sessione + genera AI summary |
| GET | `/workouts/sessions` | Lista sessioni (paginata) |
| GET | `/workouts/sessions/{id}` | Dettaglio sessione |

### Coach AI
| Metodo | Path | Descrizione |
|---|---|---|
| POST | `/coach/message` | Messaggio coach contestuale durante l'allenamento (rate limit: 3 req/min) |
| POST | `/coach/voice-response` | Risponde a input vocale dell'utente + modifiche piano strutturate |

### Nutrizione
| Metodo | Path | Descrizione |
|---|---|---|
| POST | `/nutrition/logs` | Logga un alimento |
| GET | `/nutrition/logs?date=YYYY-MM-DD` | Log del giorno |
| DELETE | `/nutrition/logs/{id}` | Elimina log |
| POST | `/nutrition/logs/photo` | Riconosce alimenti da foto (Claude Vision, max 5MB JPEG/PNG) |
| GET | `/nutrition/summary?date=YYYY-MM-DD` | Riepilogo calorie + macros + acqua del giorno |
| POST | `/nutrition/water` | Logga acqua (ml) |
| POST | `/nutrition/diet-plan/generate` | Genera piano dieta settimanale via Claude |
| GET | `/nutrition/diet-plan/current` | Piano dieta della settimana corrente |
| POST | `/nutrition/diet-plan/regenerate-day` | Rigenera un singolo giorno del piano |
| POST | `/nutrition/insights/generate` | Genera 1–3 insights AI sui pasti del giorno |
| GET | `/nutrition/insights` | Insights ultimi 7 giorni |
| PUT | `/nutrition/insights/{id}/read` | Marca insight come letto |

### Food Search
| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/food/barcode/{barcode}` | Info prodotto da codice EAN (Open Food Facts) |
| GET | `/food/search?q={query}` | Ricerca alimenti per nome (cache in memoria, TTL 1h) |

### Spotify
| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/spotify/auth-url` | URL OAuth2 Spotify |
| POST | `/spotify/callback` | Scambia code OAuth con token, salva |
| POST | `/spotify/refresh` | Rinnova access token Spotify |
| GET | `/spotify/recommendations?phase=...` | Tracce consigliate per fase allenamento (warmup/peak/recovery/cooldown) |
| GET | `/spotify/status` | Verifica se Spotify è connesso |

### Progressi
| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/progress/workouts` | Calorie per settimana, FC media, streak, totali |
| GET | `/progress/nutrition?days=7` | Calorie medie, giorni a target, trend macros |
| GET | `/progress/weekly-summary` | Riassunto testuale della settimana generato da Claude |

### Health
| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/health` | Health check per Railway |

## Database

Le tabelle principali in Supabase:

- **`users`** — profilo fitness (BMR, TDEE, obiettivi, giorni disponibili, preferenze coach)
- **`weekly_plans`** — piano settimanale AI in JSONB (esercizi, warm-up, cool-down, note per giorno)
- **`workout_sessions`** — sessioni completate con metriche e AI summary
- **`food_logs`** — log pasti con calorie e macros
- **`nutrition_insights`** — insights AI (warning / tip / positive)
- **`diet_plans`** — piano pasti settimanale AI in JSONB
- **`spotify_tokens`** — access + refresh token per utente

Lo schema SQL completo è in [`schema.sql`](schema.sql).
