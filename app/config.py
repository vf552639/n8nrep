import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Database
    SUPABASE_DB_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Security
    API_KEY: str = ""
    CORS_ORIGINS: str = "*"
    TEST_MODE: bool = False
    STRICT_VARIABLE_CHECK: bool = False
    SEQUENTIAL_MODE: bool = True

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
    SERP_CACHE_ENABLED: bool = True
    SERP_CACHE_TTL: int = 86400
    SCRAPE_CACHE_TTL: int = 43200

    # Telegram notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Content
    EXCLUDE_WORDS: str = ""
    EXCLUDED_DOMAINS: str = ""

    # Celery
    CELERY_CONCURRENCY: int = 2
    CELERY_TASK_TIME_LIMIT: int = 900

    # Fact Checking
    FACT_CHECK_ENABLED: bool = True
    FACT_CHECK_MODE: str = "soft" # "soft" or "strict"
    FACT_CHECK_FAIL_THRESHOLD: int = 1

    # Image Generation (optional)
    IMAGE_GEN_ENABLED: bool = False
    GOAPI_API_KEY: str = ""
    GOAPI_BASE_URL: str = "https://api.goapi.ai"
    IMGBB_API_KEY: str = ""
    IMAGE_POLL_INTERVAL: int = 10
    IMAGE_POLL_TIMEOUT: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
