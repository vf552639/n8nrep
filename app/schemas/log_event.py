"""Execution log line (stored in Task.log_events / SiteProject.log_events)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LogLevel(StrEnum):
    debug = "debug"
    info = "info"
    warning = "warning"
    warn = "warn"
    error = "error"


class LogEvent(BaseModel):
    """Structured event; API/UI historically use ts/msg/level/step."""

    ts: datetime | str
    level: LogLevel | str
    event: str | None = None
    step: str | None = None
    message: str | None = None
    msg: str | None = None
    duration_ms: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
