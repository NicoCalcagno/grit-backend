# GRIT — Backend
## Specifica per Claude Code / Copilot

---

## Contesto

Questo è il backend dell'app Grit — un personal trainer AI iOS. Il backend espone una REST API consumata dall'app React Native. Gestisce tutta la logica AI, le chiamate a servizi esterni, l'autenticazione e la persistenza dei dati. Il client iOS non chiama mai direttamente Claude, Spotify o Open Food Facts — passa sempre dal backend.

---

## Stack Tecnologico

| Categoria | Tecnologia |
|---|---|
| **Framework** | FastAPI (Python 3.12) |
| **Database** | Supabase (PostgreSQL) |
| **ORM** | SQLAlchemy async |
| **Autenticazione** | Supabase Auth (email/password) |
| **Storage file** | Supabase Storage (foto piatti) |
| **AI Engine** | Anthropic Claude API `claude-sonnet-4-20250514` |
| **Musica** | Spotify Web API |
| **Database alimenti** | Open Food Facts API (pubblica, no key) |
| **Validazione** | Pydantic v2 |
| **HTTP Client** | httpx (async) |
| **Hosting** | Railway |
| **Variabili ambiente** | python-dotenv |

---

## Variabili d'Ambiente

```
ANTHROPIC_API_KEY=
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
JWT_SECRET=
```

---

## Struttura Progetto

```
grit-backend/
├── main.py
├── requirements.txt
├── .env
├── .env.example
│
├── app/
│   ├── core/
│   │   ├── config.py          # Lettura variabili ambiente
│   │   ├── database.py        # Connessione Supabase / SQLAlchemy
│   │   └── auth.py            # Verifica JWT Supabase
│   │
│   ├── routers/
│   │   ├── auth.py            # Login, register, refresh token
│   │   ├── users.py           # Profilo utente
│   │   ├── workouts.py        # Piano settimanale, sessioni
│   │   ├── coach.py           # Messaggi coach AI, TTS text
│   │   ├── nutrition.py       # Food log, dieta AI, insights
│   │   ├── food_search.py     # Barcode, ricerca testo Open Food Facts
│   │   ├── spotify.py         # Auth Spotify, raccomandazioni tracce
│   │   └── progress.py        # Storico, trend, analytics
│   │
│   ├── services/
│   │   ├── claude_service.py  # Wrapper Claude API
│   │   ├── spotify_service.py # Wrapper Spotify API
│   │   ├── food_service.py    # Wrapper Open Food Facts
│   │   └── health_service.py  # Calcoli BMR, TDEE, macros
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── workout.py
│   │   ├── nutrition.py
│   │   └── progress.py
│   │
│   └── schemas/
│       ├── user.py
│       ├── workout.py
│       ├── nutrition.py
│       ├── coach.py
│       └── spotify.py
```

---

## Schema Database (Supabase / PostgreSQL)

### Tabella `users`
Estende il profilo base di Supabase Auth con i dati fitness dell'utente.

Campi: id (FK auth.users), name, age, weight_kg, height_cm, gender, fitness_level, goals (array), available_days, preferred_workouts (array), coach_language, coach_tone, onboarding_completed, created_at, updated_at

### Tabella `weekly_plans`
Piano settimanale generato da Claude.

Campi: id, user_id (FK), week_start_date, plan_json (JSONB — struttura completa del piano), generated_at

### Tabella `workout_sessions`
Sessioni di allenamento completate.

Campi: id, user_id (FK), plan_id (FK nullable), started_at, completed_at, duration_minutes, calories_burned, avg_heart_rate, perceived_exertion, exercises_completed, exercises_skipped, ai_summary, created_at

### Tabella `food_logs`
Ogni alimento loggato dall'utente.

Campi: id, user_id (FK), logged_at, meal_type (breakfast/lunch/dinner/snack), food_name, quantity_grams, calories, protein_g, carbs_g, fat_g, source (barcode/photo/manual), barcode (nullable), photo_url (nullable), created_at

### Tabella `nutrition_insights`
Insights AI generati da Claude sull'alimentazione.

Campi: id, user_id (FK), generated_at, insight_text, insight_type (warning/tip/positive), read, created_at

### Tabella `diet_plans`
Piano dieta settimanale generato da Claude.

Campi: id, user_id (FK), week_start_date, plan_json (JSONB), generated_at

### Tabella `spotify_tokens`
Token Spotify per utente.

Campi: user_id (FK), access_token, refresh_token, expires_at, updated_at

---

## Feature e Macro Task

---

### FEATURE 1 — Autenticazione

**Task:**
- Endpoint `POST /auth/register` — crea utente su Supabase Auth + riga in tabella `users`
- Endpoint `POST /auth/login` — restituisce JWT Supabase
- Endpoint `POST /auth/refresh` — rinnova il JWT
- Endpoint `POST /auth/logout`
- Middleware di autenticazione: tutti gli endpoint (eccetto auth) verificano il JWT Supabase nell'header `Authorization: Bearer <token>`
- Helper `get_current_user` iniettato come dipendenza FastAPI su ogni route protetta

---

### FEATURE 2 — Profilo Utente

**Task:**
- Endpoint `GET /users/me` — restituisce profilo completo
- Endpoint `PUT /users/me` — aggiorna profilo (peso, obiettivi, preferenze coach, ecc.)
- Endpoint `DELETE /users/me` — cancella account e tutti i dati associati
- Calcolo automatico BMR e TDEE salvato e aggiornato ad ogni modifica di peso/età/livello attività

---

### FEATURE 3 — Piano Settimanale AI

**Task:**
- Endpoint `POST /workouts/weekly-plan/generate` — chiama Claude API con profilo utente + ultime 5 sessioni come contesto, restituisce piano settimanale strutturato in JSON, salva in tabella `weekly_plans`
- Endpoint `GET /workouts/weekly-plan/current` — restituisce il piano della settimana corrente
- Endpoint `POST /workouts/weekly-plan/regenerate` — forza rigenerazione del piano
- Il piano JSON include per ogni giorno: tipo workout, lista esercizi (nome, muscoli, serie, rep, recupero), warm-up, cool-down, note AI, oppure flag `is_rest: true` con motivazione

---

### FEATURE 4 — Gestione Sessione Workout

**Task:**
- Endpoint `POST /workouts/sessions` — crea una nuova sessione (salva started_at, piano di riferimento)
- Endpoint `PUT /workouts/sessions/{id}` — aggiorna sessione in corso (calorie, FC, perceived_exertion)
- Endpoint `POST /workouts/sessions/{id}/complete` — chiude la sessione, chiama Claude per generare l'ai_summary, salva tutto
- Endpoint `GET /workouts/sessions` — lista sessioni passate con paginazione
- Endpoint `GET /workouts/sessions/{id}` — dettaglio singola sessione

---

### FEATURE 5 — Coach AI

**Task:**
- Endpoint `POST /coach/message` — riceve il contesto della sessione (esercizio corrente, serie, rep, FC, fatica percepita, minuti trascorsi, ultimo input vocale utente) + evento che ha triggerato il messaggio (exercise_start, mid_set, rest_start, ecc.) → chiama Claude → restituisce testo da sintetizzare vocalmente lato client
- Il prompt a Claude è costruito con: tono preferito dall'utente, lingua, contesto sessione
- Rate limiting server-side: max 3 richieste/minuto per utente per questo endpoint
- Endpoint `POST /coach/voice-response` — riceve il testo trascritto dall'utente via STT + contesto sessione → Claude genera risposta + eventuale modifica al piano (es. riduci set, salta esercizio) → restituisce risposta testuale + istruzioni di modifica strutturate

---

### FEATURE 6 — Musica Spotify

**Task:**
- Endpoint `GET /spotify/auth-url` — genera URL OAuth2 Spotify con scopes necessari
- Endpoint `POST /spotify/callback` — riceve il code OAuth, scambia con access + refresh token, salva in tabella `spotify_tokens`
- Endpoint `POST /spotify/refresh` — rinnova access token Spotify se scaduto
- Endpoint `GET /spotify/recommendations` — riceve fase allenamento (warmup/peak/recovery/cooldown) + fatica percepita → chiama Spotify Recommendations API con parametri BPM ed energia appropriati → restituisce lista tracce consigliate
- Endpoint `GET /spotify/status` — verifica se l'utente ha Spotify connesso

---

### FEATURE 7 — Food Search

**Task:**
- Endpoint `GET /food/barcode/{barcode}` — chiama Open Food Facts API con il codice EAN → restituisce nome prodotto, brand, calorie per 100g, macros per 100g
- Endpoint `GET /food/search?q={query}` — chiama Open Food Facts search → restituisce lista risultati con nome, brand, calorie per 100g, macros per 100g
- Gestione cache in memoria (TTL 1 ora) per le query più frequenti su Open Food Facts

---

### FEATURE 8 — Food Log

**Task:**
- Endpoint `POST /nutrition/logs` — salva un log pasto (name, quantity_grams, meal_type, source, barcode opzionale)
- Endpoint `GET /nutrition/logs?date={date}` — restituisce tutti i log di un giorno specifico
- Endpoint `DELETE /nutrition/logs/{id}` — elimina un log
- Endpoint `POST /nutrition/logs/photo` — riceve immagine base64 → salva su Supabase Storage → invia a Claude Vision con prompt per riconoscimento alimenti → restituisce lista alimenti riconosciuti con calorie e macros stimati → il client mostra i risultati per conferma prima del salvataggio

---

### FEATURE 9 — Dashboard Nutrizionale

**Task:**
- Endpoint `GET /nutrition/summary?date={date}` — restituisce: totale calorie del giorno, breakdown macros, target calorico (BMR + calorie bruciate da HealthKit passate dal client), lista log raggruppati per pasto, percentuale raggiungimento target, grammi acqua loggati
- Endpoint `POST /nutrition/water` — logga un bicchiere d'acqua per la data indicata
- Il target calorico viene calcolato server-side ricevendo le calorie bruciate dal client (dati HealthKit)

---

### FEATURE 10 — Piano Dieta AI

**Task:**
- Endpoint `POST /nutrition/diet-plan/generate` — chiama Claude con profilo utente (BMR, TDEE, obiettivi) → genera piano pasti settimanale strutturato in JSON (colazione, pranzo, cena, snack per ogni giorno con calorie e macros) → salva in tabella `diet_plans`
- Endpoint `GET /nutrition/diet-plan/current` — restituisce il piano della settimana corrente
- Endpoint `POST /nutrition/diet-plan/regenerate-day` — rigenera il piano per un singolo giorno
- I giorni di allenamento hanno target calorici più alti dei giorni di riposo

---

### FEATURE 11 — Insights AI Nutrizione

**Task:**
- Endpoint `POST /nutrition/insights/generate` — chiama Claude con: log pasti del giorno, calorie totali, macros, workout del giorno (se presente), obiettivi utente → genera 1-3 insights proattivi → salva in tabella `nutrition_insights`
- Endpoint `GET /nutrition/insights` — restituisce gli ultimi 7 giorni di insights
- Endpoint `PUT /nutrition/insights/{id}/read` — marca un insight come letto
- Gli insights hanno un tipo: `warning` (attenzione), `tip` (consiglio), `positive` (rinforzo positivo)

---

### FEATURE 12 — Progressi e Analytics

**Task:**
- Endpoint `GET /progress/workouts` — calorie bruciate per settimana, FC media per sessione, streak allenamento, totale sessioni, totale minuti allenati
- Endpoint `GET /progress/nutrition` — calorie medie giornaliere ultimi 7/30 giorni, giorni in cui il target è stato rispettato, trend macros settimanali
- Endpoint `GET /progress/weekly-summary` — chiama Claude con dati workout + nutrizione della settimana → genera testo riassuntivo con valutazione e consigli → restituisce testo

---

## Note Architetturali

- Tutti gli endpoint sono async
- Usare `httpx.AsyncClient` per tutte le chiamate HTTP esterne (Claude, Spotify, Open Food Facts)
- Le risposte JSON di Claude vanno sempre parsate con try/except — in caso di errore restituire un fallback strutturato
- Il rate limiting del coach (3 req/min per utente) va implementato in memoria con un dizionario `{user_id: [timestamps]}`
- Le immagini ricevute via base64 vanno validate (max 5MB, solo JPEG/PNG) prima di essere processate
- Tutti gli errori restituiscono `{"error": "messaggio"}` con HTTP status code appropriato
- CORS configurato per accettare richieste dall'app mobile
- Health check endpoint `GET /health` per Railway

---

*Grit Backend v1.0 — FastAPI + Supabase*
