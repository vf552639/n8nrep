from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    SUPABASE_DB_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    # Recycle connections before Supavisor/NAT idle kills them (see task59).
    DB_POOL_RECYCLE_SECONDS: int = 60

    # Logging
    LOG_JSON: bool = False
    LOG_LEVEL: str = "INFO"

    # Security — set AUTH_DISABLED=true only for CI/local; never in production.
    API_KEY: str = ""
    AUTH_DISABLED: bool = False
    CORS_ORIGINS: str = "*"
    TEST_MODE: bool = False
    STRICT_VARIABLE_CHECK: bool = False
    SEQUENTIAL_MODE: bool = True

    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    OPENROUTER_API_KEY: str
    # Sent as HTTP-Referer to OpenRouter (public site URL for their stats).
    OPENROUTER_HTTP_REFERER: str = "https://example.com"
    DEFAULT_MODEL: str = "openai/gpt-5"
    ANALYST_MODEL: str = "google/gemini-2.5-pro"
    LLM_REQUEST_TIMEOUT: int = 600
    # Comma-separated model=seconds overrides, e.g. "openai/gpt-5-mini=900,openai/gpt-5=900"
    LLM_MODEL_TIMEOUTS: str = ""
    # Primary=pipe|separated|fallbacks, e.g. "openai/gpt-5-mini=openai/gpt-5|anthropic/claude-sonnet-4"
    LLM_MODEL_FALLBACKS: str = ""

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
    STEP_TIMEOUT_MINUTES: int = 30
    PIPELINE_STEP_TIMEOUT_SECONDS: int = 1800
    PROJECT_PAGE_APPROVAL: bool = False

    # Fact Checking
    FACT_CHECK_ENABLED: bool = True
    FACT_CHECK_MODE: str = "soft"  # "soft" or "strict"
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def require_api_key_unless_auth_disabled(self) -> "Settings":
        if not self.AUTH_DISABLED and not (self.API_KEY or "").strip():
            raise ValueError(
                "API_KEY is required when AUTH_DISABLED is false. "
                "For CI/local tests set AUTH_DISABLED=true, or set a non-empty API_KEY in .env."
            )
        return self


settings = Settings()
