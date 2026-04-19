from pydantic import BaseModel, field_validator

from app.utils.language_normalize import normalize_language


class AuthorCreate(BaseModel):
    author: str
    country: str
    language: str
    bio: str | None = None
    co_short: str | None = None
    city: str | None = None
    imitation: str | None = None
    year: str | None = None
    face: str | None = None
    target_audience: str | None = None
    rhythms_style: str | None = None
    exclude_words: str | None = None

    @field_validator("language")
    @classmethod
    def normalize_language_field(cls, v: str) -> str:
        out = normalize_language(v) or ""
        if not out:
            raise ValueError("Language is required")
        return out
