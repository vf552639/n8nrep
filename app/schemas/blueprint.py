from pydantic import BaseModel, field_validator

from app.services.pipeline_presets import VALID_PRESETS


class SiteBlueprintCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True


class BlueprintPageCreate(BaseModel):
    page_slug: str
    page_title: str
    page_type: str = "article"
    keyword_template: str
    keyword_template_brand: str | None = None
    filename: str
    sort_order: int = 0
    nav_label: str | None = None
    show_in_nav: bool = True
    show_in_footer: bool = True
    use_serp: bool = True
    pipeline_preset: str = "full"
    pipeline_steps_custom: list[str] | None = None
    default_legal_template_id: str | None = None

    @field_validator("pipeline_preset")
    @classmethod
    def validate_pipeline_preset(cls, v: str) -> str:
        s = (v or "full").strip().lower()
        if s not in VALID_PRESETS:
            raise ValueError(f"pipeline_preset must be one of {sorted(VALID_PRESETS)}, got {v!r}")
        return s
