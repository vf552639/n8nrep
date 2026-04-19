from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    html_template: str = Field(..., min_length=1)
    description: str | None = None
    preview_screenshot: str | None = Field(None, max_length=500)
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    html_template: str | None = None
    description: str | None = None
    preview_screenshot: str | None = Field(None, max_length=500)
    is_active: bool | None = None
