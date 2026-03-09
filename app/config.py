import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database
    SUPABASE_DB_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    OPENROUTER_API_KEY: str
    DEFAULT_MODEL: str = "openai/gpt-5"
    ANALYST_MODEL: str = "google/gemini-2.5-pro"

    # SERP & Scraping
    DATAFORSEO_LOGIN: str = ""
    DATAFORSEO_PASSWORD: str = ""
    SERPER_API_KEY: str = ""
    SERPAPI_KEY: str = ""

    # Telegram notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Content
    EXCLUDE_WORDS: str = ""

    # Celery
    CELERY_CONCURRENCY: int = 2
    CELERY_TASK_TIME_LIMIT: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
