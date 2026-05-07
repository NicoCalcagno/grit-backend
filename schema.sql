-- Schema per Grit Backend su Supabase PostgreSQL
-- Eseguire nell'editor SQL di Supabase

-- Tabella users (estende auth.users)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT,
    age INTEGER,
    weight_kg FLOAT,
    height_cm FLOAT,
    gender TEXT,
    fitness_level TEXT,
    goals TEXT[],
    available_days TEXT[],
    preferred_workouts TEXT[],
    coach_language TEXT DEFAULT 'it',
    coach_tone TEXT DEFAULT 'motivating',
    onboarding_completed BOOLEAN DEFAULT FALSE,
    bmr FLOAT,
    tdee FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabella weekly_plans
CREATE TABLE IF NOT EXISTS public.weekly_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    week_start_date TIMESTAMPTZ NOT NULL,
    plan_json JSONB NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabella workout_sessions
CREATE TABLE IF NOT EXISTS public.workout_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES public.weekly_plans(id) ON DELETE SET NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_minutes INTEGER,
    calories_burned FLOAT,
    avg_heart_rate INTEGER,
    perceived_exertion INTEGER CHECK (perceived_exertion BETWEEN 1 AND 10),
    exercises_completed JSONB,
    exercises_skipped JSONB,
    ai_summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabella food_logs
CREATE TABLE IF NOT EXISTS public.food_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    logged_at TIMESTAMPTZ NOT NULL,
    meal_type TEXT NOT NULL CHECK (meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')),
    food_name TEXT NOT NULL,
    quantity_grams FLOAT NOT NULL,
    calories FLOAT NOT NULL,
    protein_g FLOAT,
    carbs_g FLOAT,
    fat_g FLOAT,
    source TEXT NOT NULL DEFAULT 'manual',
    barcode TEXT,
    photo_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabella nutrition_insights
CREATE TABLE IF NOT EXISTS public.nutrition_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    insight_text TEXT NOT NULL,
    insight_type TEXT NOT NULL CHECK (insight_type IN ('warning', 'tip', 'positive')),
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabella diet_plans
CREATE TABLE IF NOT EXISTS public.diet_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    week_start_date TIMESTAMPTZ NOT NULL,
    plan_json JSONB NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabella spotify_tokens
CREATE TABLE IF NOT EXISTS public.spotify_tokens (
    user_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabella water_logs
CREATE TABLE IF NOT EXISTS public.water_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    logged_at TIMESTAMPTZ NOT NULL,
    amount_ml INTEGER NOT NULL DEFAULT 250,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_id ON public.workout_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_food_logs_user_id_logged_at ON public.food_logs(user_id, logged_at);
CREATE INDEX IF NOT EXISTS idx_nutrition_insights_user_id ON public.nutrition_insights(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_weekly_plans_user_id ON public.weekly_plans(user_id, week_start_date);
CREATE INDEX IF NOT EXISTS idx_diet_plans_user_id ON public.diet_plans(user_id, week_start_date);
CREATE INDEX IF NOT EXISTS idx_water_logs_user_id ON public.water_logs(user_id, logged_at);

-- Row Level Security (opzionale ma consigliato)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weekly_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workout_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.food_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nutrition_insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.diet_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spotify_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.water_logs ENABLE ROW LEVEL SECURITY;

-- Il backend usa service_role key quindi bypassa RLS automaticamente
