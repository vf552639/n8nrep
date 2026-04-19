"""Shape hints for SiteProject.project_keywords JSONB."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProjectKeywords(BaseModel):
    model_config = {"extra": "allow"}

    raw: list[str] = Field(default_factory=list)
    clustered: dict[str, Any] = Field(default_factory=dict)
    unassigned: list[str] = Field(default_factory=list)
