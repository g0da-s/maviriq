import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API Keys
    anthropic_api_key: str
    serper_api_key: str

    # Google
    google_api_key: str = ""

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
    search_cache_ttl: int = 86400  # 24 hours

    # Pipeline
    max_search_queries_per_agent: int = 8
    max_pain_points: int = 15
    max_competitors: int = 10
    agent_timeout: int = 120  # seconds per agent before giving up
    agent_max_iterations: int = 10  # max tool-use loop iterations per agent

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

# LangSmith reads directly from os.environ.
# Force the .env file values so stale shell exports don't interfere.
_langsmith_vars = {"LANGSMITH_TRACING", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "LANGSMITH_ENDPOINT"}
_dotenv_values: dict[str, str] = {}
try:
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k in _langsmith_vars and v:
                    _dotenv_values[k] = v
except FileNotFoundError:
    pass

os.environ["LANGSMITH_TRACING"] = _dotenv_values.get(
    "LANGSMITH_TRACING", settings.langsmith_tracing
)
if _dotenv_values.get("LANGSMITH_API_KEY") or settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = _dotenv_values.get(
        "LANGSMITH_API_KEY", settings.langsmith_api_key
    )
os.environ["LANGSMITH_PROJECT"] = _dotenv_values.get(
    "LANGSMITH_PROJECT", settings.langsmith_project
)
os.environ["LANGSMITH_ENDPOINT"] = _dotenv_values.get(
    "LANGSMITH_ENDPOINT", settings.langsmith_endpoint
)
