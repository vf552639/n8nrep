from pydantic import BaseModel


class SettingsUpdate(BaseModel):
    OPENROUTER_API_KEY: str | None = None
    DATAFORSEO_LOGIN: str | None = None
    DATAFORSEO_PASSWORD: str | None = None
    SERPAPI_KEY: str | None = None
    SERPER_API_KEY: str | None = None
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None
    CELERY_CONCURRENCY: str | None = None
    EXCLUDE_WORDS: str | None = None
    EXCLUDED_DOMAINS: str | None = None
    SEQUENTIAL_MODE: str | None = None
    MIDJOURNEY_API_KEY: str | None = None
    IMGBB_API_KEY: str | None = None
    IMAGE_MODEL_DEFAULT: str | None = None
    IMAGE_GEN_ENABLED: str | None = None
