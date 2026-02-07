from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://localhost/indexing_service"
    DATABASE_URL_SYNC: str = "postgresql://localhost/indexing_service"
    REDIS_URL: str = "redis://localhost:6379/0"
    GOOGLE_CUSTOM_SEARCH_API_KEY: str = ""
    GOOGLE_CSE_ID: str = ""
    SECRET_KEY: str = "change-me"
    CREDENTIALS_DIR: str = "./credentials"
    SITEMAPS_DIR: str = "./sitemaps"
    BASE_URL: str = "http://localhost:8000"

    # SMTP settings for email digest
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}


settings = Settings()
