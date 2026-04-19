from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.serp_config import SerpConfig


class TaskCreate(BaseModel):
    main_keyword: str
    country: str
    language: str
    target_site: str
    author_id: int | None = None
    additional_keywords: str | None = None
    priority: int = 0
    page_type: str = "article"
    serp_config: SerpConfig | None = None

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        v = (v or "").strip().upper()
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Country must be a 2-letter ISO code (e.g. DE, FR, US)")
        return v


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    main_keyword: str
    status: str
    created_at: str


class FetchUrlMetaRequest(BaseModel):
    url: str


class UpdateStepResultRequest(BaseModel):
    step_name: str
    result: str


class StartSelectedRequest(BaseModel):
    task_ids: list[str]


class ForceStatusRequest(BaseModel):
    action: str  # "complete" or "fail"


class RerunStepRequest(BaseModel):
    step_name: str
    feedback: str
    cascade: bool = True


class ApproveSerpUrlsRequest(BaseModel):
    urls: list[str]


class ApproveImagesRequest(BaseModel):
    approved_ids: list
    skipped_ids: list = []


class RegenerateImageRequest(BaseModel):
    image_id: str
    new_prompt: str = ""
