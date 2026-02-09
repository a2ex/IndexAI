from pydantic_settings import BaseSettings
from pydantic import model_validator
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://localhost/indexing_service"
    DATABASE_URL_SYNC: str = "postgresql://localhost/indexing_service"
    REDIS_URL: str = "redis://localhost:6379/0"
    GOOGLE_CUSTOM_SEARCH_API_KEY: str = ""
    GOOGLE_CSE_ID: str = ""
    GSC_PROPERTY: str = ""
    GSC_SERVICE_ACCOUNT_JSON: str = ""
    INDEXNOW_API_KEY: str = ""
    SECRET_KEY: str = "change-me"
    CREDENTIALS_DIR: str = "./credentials"
    SITEMAPS_DIR: str = "./sitemaps"
    BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    STATIC_DIR: str = ""

    # SMTP settings for email digest
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    model_config = {"env_file": "../.env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def fix_database_url(self) -> "Settings":
        # Railway provides postgresql:// — convert to postgresql+asyncpg://
        if self.DATABASE_URL.startswith("postgresql://"):
            self.DATABASE_URL = self.DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self


settings = Settings()
