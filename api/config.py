"""Centralized config via Pydantic Settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = ""
    db_host: str = ""
    db_port: str = "5432"
    db_name: str = "qauto"
    db_user: str = "postgres"
    db_password: str = ""
    db_sslmode: str = ""
    redis_url: str = "redis://localhost:6379"
    groq_api_key: str = ""
    sentry_dsn: str = ""
    environment: str = "local"
    debug: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
