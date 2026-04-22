from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.services.url_utils import normalize_url

MAX_PROJECT_COMPETITOR_URLS = 50


def _validate_competitor_urls_value(v: Any) -> list[str]:
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError("competitor_urls must be a list of strings")
    if len(v) > MAX_PROJECT_COMPETITOR_URLS:
        raise ValueError(f"Maximum {MAX_PROJECT_COMPETITOR_URLS} competitor URLs allowed")
    out: list[str] = []
    for raw in v:
        if raw is None:
            continue
        s = str(raw).strip()
        if not s:
            continue
        norm = normalize_url(s)
        if norm:
            out.append(norm)
    return out


class SiteProjectCreate(BaseModel):
    name: str
    blueprint_id: str
    seed_keyword: str
    seed_is_brand: bool = False
    target_site: str | None = None
    country: str
    language: str
    author_id: int | None = None
    serp_config: dict[str, Any] | None = None
    project_keywords: dict[str, Any] | None = None
    legal_template_map: dict[str, str] | None = None
    use_site_template: bool = True
    competitor_urls: list[str] | None = None

    @field_validator("competitor_urls", mode="before")
    @classmethod
    def validate_competitor_urls_create(cls, v: Any) -> list[str]:
        return _validate_competitor_urls_value(v)

    @field_validator("target_site", mode="before")
    @classmethod
    def normalize_target_site_create(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
        return v


class ClusterKeywordsRequest(BaseModel):
    keywords: list[str]
    blueprint_id: str


class ProjectPreviewRequest(BaseModel):
    blueprint_id: str
    seed_keyword: str
    seed_is_brand: bool = False
    target_site: str | None = None
    country: str
    language: str
    author_id: int | None = None
    serp_config: dict[str, Any] | None = None
    use_site_template: bool = True

    @field_validator("target_site", mode="before")
    @classmethod
    def normalize_target_site_preview(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("country")
    @classmethod
    def validate_country_preview(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
        return v


class SiteProjectCloneBody(BaseModel):
    name: str | None = None
    seed_keyword: str | None = None
    seed_is_brand: bool | None = None
    target_site: str | None = None
    country: str | None = None
    language: str | None = None
    author_id: int | None = None
    legal_template_map: dict[str, str] | None = None
    use_site_template: bool | None = None
    competitor_urls: list[str] | None = None

    @field_validator("competitor_urls", mode="before")
    @classmethod
    def validate_competitor_urls_clone(cls, v: Any) -> list[str] | None:
        if v is None:
            return None
        return _validate_competitor_urls_value(v)

    @field_validator("target_site", mode="before")
    @classmethod
    def normalize_target_site_clone(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @field_validator("country")
    @classmethod
    def validate_country_clone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
        return v


class DeleteSelectedProjectsRequest(BaseModel):
    project_ids: list[str]
    force: bool = False


class SiteProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    blueprint_id: str
    site_id: str
    seed_keyword: str
    seed_is_brand: bool
    status: str
    current_page_index: int
    build_zip_url: str | None
    created_at: str
    competitor_urls: list[str] = []
