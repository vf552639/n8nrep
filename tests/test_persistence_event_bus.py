import asyncio
import os

os.environ.setdefault("DESKTOP_MODE", "true")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/test_persistence_eb.sqlite")
os.environ.setdefault("AUTH_DISABLED", "true")

import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_add_log_publishes_to_event_bus():
    from app.services import event_bus

    loop = asyncio.get_event_loop()
    event_bus.init(loop)
    q = event_bus.subscribe("task:test-task-123")

    db = MagicMock()
    task = MagicMock()
    task.id = "test-task-123"
    task.project_id = "proj-456"
    task.log_events = []

    from app.services.pipeline.persistence import add_log

    with patch("app.services.pipeline.persistence.append_log_event", return_value=[]):
        add_log(db, task, "pipeline step done", level="info", step="serp")

    await asyncio.sleep(0)
    assert not q.empty()
    evt = q.get_nowait()
    assert evt["msg"] == "pipeline step done"
    event_bus.unsubscribe("task:test-task-123", q)
