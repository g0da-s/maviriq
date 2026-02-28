import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API Keys
    anthropic_api_key: str
    serper_api_key: str

    # Google
    google_api_key: str = ""

    # OpenAI (Whisper STT)
    openai_api_key: str = ""

    # LLM Models
    reasoning_model: str = "claude-sonnet-4-5-20250929"
    cheap_model: str = "claude-haiku-4-5-20251001"
    research_model: str = "gemini-2.0-flash"

    # Serper
    serper_base_url: str = "https://google.serper.dev"
    serper_max_concurrent: int = 10

    # CORS (required — comma-separated origins, e.g. "http://localhost:3000,https://myapp.com")
    cors_origins: str

    # Redis (optional — falls back to in-memory rate limiting if not set)
    redis_url: str = ""

    # Supabase (required — app will fail to start if missing)
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str

    # Search cache TTL (seconds)
    search_cache_ttl: int = 600  # 10 minutes

    # Pipeline
    agent_timeout: int = 120  # seconds per agent before giving up
    agent_max_iterations: int = 10  # max tool-use loop iterations per agent
    anthropic_max_concurrent: int = 5  # Tier 2: bumped from 2

    # LangSmith
    langsmith_tracing: str = "true"
    langsmith_api_key: str = ""
    langsmith_project: str = "maviriq"
    langsmith_endpoint: str = "https://eu.api.smith.langchain.com"

    # Stripe (required — app will fail to start if missing)
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_price_5: str
    stripe_price_20: str
    stripe_price_50: str
    frontend_url: str = "http://localhost:3000"


settings = Settings()  # type: ignore[call-arg]

# LangSmith reads os.environ directly, so propagate the resolved settings values.
os.environ["LANGSMITH_TRACING"] = settings.langsmith_tracing
if settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
