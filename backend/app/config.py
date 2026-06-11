from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://velvyko:velvyko@localhost:5432/velvyko"

    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    llm_provider: str = "anthropic"           # anthropic | openai
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    daily_budget_usd: float = 20.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_cooldown_s: int = 60
    llm_timeout_s: float = 30.0

    lookup_timeout_s: float = 8.0
    lookup_cache_ttl_days: int = 30
    crossref_mailto: str = "admin@srv1533829.hstgr.cloud"


@lru_cache
def get_settings() -> Settings:
    return Settings()
