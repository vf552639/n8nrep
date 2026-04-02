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
    LLM_REQUEST_TIMEOUT: int = 300

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
    CELERY_TASK_TIME_LIMIT: int = 1800
    CELERY_SOFT_TIME_LIMIT: int = 1500
    STALE_TASK_TIMEOUT_MINUTES: int = 15
    STEP_TIMEOUT_MINUTES: int = 15
    PIPELINE_STEP_TIMEOUT_SECONDS: int = 900
    PROJECT_PAGE_APPROVAL: bool = False

    # Fact Checking
    FACT_CHECK_ENABLED: bool = True
    FACT_CHECK_MODE: str = "soft" # "soft" or "strict"
    FACT_CHECK_FAIL_THRESHOLD: int = 1

    # Self-check / retry budgets (exclude-word retries, html_structure recovery)
    SELF_CHECK_MAX_RETRIES: int = 1
    SELF_CHECK_MAX_COST_PER_STEP: float = 0.10

    # Keyword clustering (project additional keywords → blueprint pages)
    CLUSTERING_MODEL: str = "openai/gpt-4o"
    MAX_PROJECT_KEYWORDS: int = 100

    # Image Generation (optional) — OpenRouter image models + ImgBB hosting
    IMAGE_GEN_ENABLED: bool = False
    IMGBB_API_KEY: str = ""
    IMAGE_MODEL_DEFAULT: str = "google/gemini-2.5-flash-image-preview"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
