import asyncio
import os

os.environ.setdefault("DESKTOP_MODE", "true")
os.environ.setdefault("SQLITE_DB_PATH", "/tmp/test_sse.sqlite")
os.environ.setdefault("AUTH_DISABLED", "true")

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_project_events_returns_event_stream():
    from app.main import app
    from app.services import event_bus

    # Initialise the event bus on the running loop (lifespan would do this in production).
    event_bus.init(asyncio.get_running_loop())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:

        async def _emit():
            await asyncio.sleep(0.1)
            event_bus.publish("project:proj-1", {"type": "done", "status": "completed"})

        asyncio.create_task(_emit())

        chunks = []
        async with client.stream("GET", "/api/sse/projects/proj-1/events") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            async for line in resp.aiter_lines():
                chunks.append(line)
                if '"type": "done"' in line or '"type":"done"' in line:
                    break

    assert any("done" in c for c in chunks)
