from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, coach, food_search, nutrition, progress, spotify, users, workouts

app = FastAPI(
    title="Grit Backend",
    description="Personal trainer AI backend — FastAPI + Supabase",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workouts.router)
app.include_router(coach.router)
app.include_router(nutrition.router)
app.include_router(food_search.router)
app.include_router(spotify.router)
app.include_router(progress.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "grit-backend"}
