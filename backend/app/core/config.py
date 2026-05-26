from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "ArmorScan AI"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://armorscan:armorscan@localhost:5432/armorscan"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # AI
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_REASONING_EFFORT: str = "medium"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ArmorIQ
    ARMORIQ_API_KEY: str = ""
    ARMORIQ_API_URL: str = "https://api.armoriq.ai"

    @property
    def effective_groq_api_key(self) -> str:
        return self.GROQ_API_KEY or self.OPENAI_API_KEY


settings = Settings()
