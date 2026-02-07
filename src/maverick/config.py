from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # API Keys
    anthropic_api_key: str
    serper_api_key: str

    # LLM Models
    reasoning_model: str = "claude-sonnet-4-5-20250929"
    cheap_model: str = "claude-haiku-4-5-20251001"

    # Serper
    serper_base_url: str = "https://google.serper.dev"
    serper_max_concurrent: int = 10

    # Database
    database_url: str = "sqlite+aiosqlite:///maverick.db"

    # Search cache TTL (seconds)
    search_cache_ttl: int = 86400  # 24 hours

    # Pipeline
    max_search_queries_per_agent: int = 8
    max_pain_points: int = 15
    max_competitors: int = 10


settings = Settings()  # type: ignore[call-arg]
