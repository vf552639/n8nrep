"""Contracts for Task.step_results JSONB (documentation + optional validation)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    completed_with_warnings = "completed_with_warnings"
    failed = "failed"
    skipped = "skipped"


class StepResult(BaseModel):
    model_config = {"extra": "allow"}

    status: StepStatus | str
    started_at: datetime | str | None = None
    finished_at: datetime | str | None = None
    model: str | None = None
    result: Any = None
    error: str | None = None


class PipelinePlan(BaseModel):
    model_config = {"extra": "allow"}

    steps: list[str]
    preset: str | None = None


class TaskStepResults(BaseModel):
    """Subset of keys; full step_results dict may contain many pipeline keys."""

    model_config = {"populate_by_name": True, "extra": "allow"}

    pipeline_plan: PipelinePlan | None = Field(default=None, validation_alias="_pipeline_plan")
