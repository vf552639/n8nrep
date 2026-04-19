"""Worker wiring without full Celery/Redis."""

import structlog


def test_context_cleared_after_bind(monkeypatch):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(task_id="abc")
    assert structlog.contextvars.get_contextvars().get("task_id") == "abc"
    structlog.contextvars.clear_contextvars()
    assert structlog.contextvars.get_contextvars().get("task_id") is None
