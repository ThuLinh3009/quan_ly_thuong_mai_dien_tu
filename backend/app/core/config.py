from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TBookStore API"
    database_url: str = "postgresql://tbookstore:tbookstore@localhost:5432/tbookstore"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    cors_origins: list[str] = ["http://localhost:4200"]
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    # Rate limit chung theo IP (request/phút). Login có giới hạn riêng 10 lần/phút.
    rate_limit_per_minute: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
