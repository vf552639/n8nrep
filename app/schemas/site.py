from pydantic import BaseModel, field_validator

from app.utils.language_normalize import normalize_language


class SiteCreate(BaseModel):
    name: str
    domain: str
    country: str
    language: str
    is_active: bool = True
    template_id: str | None = None
    legal_info: dict | None = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
        return v

    @field_validator("language")
    @classmethod
    def normalize_language_create(cls, v: str) -> str:
        out = normalize_language(v) or ""
        if not out:
            raise ValueError("Language is required")
        return out


class SiteUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    country: str | None = None
    language: str | None = None
    is_active: bool | None = None
    template_id: str | None = None
    legal_info: dict | None = None

    @field_validator("country")
    @classmethod
    def validate_country_optional(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
        return v

    @field_validator("language")
    @classmethod
    def normalize_language_update(cls, v: str | None) -> str | None:
        if v is None:
            return v
        out = normalize_language(v)
        return out if out else None
