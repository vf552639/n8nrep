from pydantic import BaseModel, Field


class LegalPageCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    page_type: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1)
    content_format: str = Field(default="text", pattern="^(text|html)$")
    variables: dict = Field(default_factory=dict)
    notes: str | None = None
    is_active: bool = True


class LegalPageUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    page_type: str | None = Field(None, min_length=1, max_length=50)
    content: str | None = None
    content_format: str | None = Field(None, pattern="^(text|html)$")
    variables: dict | None = None
    notes: str | None = None
    is_active: bool | None = None
