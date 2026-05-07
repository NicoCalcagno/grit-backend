from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    spotify_client_id: str
    spotify_client_secret: str
    spotify_redirect_uri: str = "http://localhost:8000/spotify/callback"
    supabase_url: str
    supabase_service_key: str
    jwt_secret: str = ""  # usato solo per token legacy HS256
    database_url: str
    claude_model: str = "claude-sonnet-4-20250514"

    model_config = {"env_file": ".env"}


settings = Settings()
