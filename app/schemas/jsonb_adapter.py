"""Optional strict validation helpers for JSONB fields."""

from __future__ import annotations

import contextlib
from typing import Any

from pydantic import TypeAdapter

from app.schemas.log_event import LogEvent
from app.schemas.step_result import TaskStepResults

_step_results_adapter = TypeAdapter(TaskStepResults)
_log_events_adapter = TypeAdapter(list[LogEvent])


def read_step_results(raw: dict | None) -> dict[str, Any]:
    """Return raw dict; attempt validation for observability only."""
    data = raw or {}
    with contextlib.suppress(Exception):
        _step_results_adapter.validate_python(data)
    return data


def write_step_results(obj: TaskStepResults) -> dict[str, Any]:
    return obj.model_dump(by_alias=True, mode="json", exclude_none=True)


def read_log_events(raw: list | None) -> list[LogEvent]:
    try:
        return _log_events_adapter.validate_python(raw or [])
    except Exception:
        return []


def append_log_event(raw: list | None, event: LogEvent, max_len: int = 500) -> list[dict[str, Any]]:
    events = read_log_events(raw)
    events.append(event)
    if len(events) > max_len:
        events = events[-max_len:]
    return [e.model_dump(mode="json", exclude_none=True) for e in events]
