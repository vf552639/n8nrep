import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services import event_bus

router = APIRouter()

_KEEPALIVE_TIMEOUT = 30  # seconds


async def _stream(key: str):
    q = event_bus.subscribe(key)
    try:
        while True:
            try:
                evt = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_TIMEOUT)
                yield f"data: {json.dumps(evt)}\n\n"
                if evt.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    finally:
        event_bus.unsubscribe(key, q)


@router.get("/projects/{project_id}/events")
async def project_events(project_id: str):
    return StreamingResponse(
        _stream(f"project:{project_id}"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/tasks/{task_id}/events")
async def task_events(task_id: str):
    return StreamingResponse(
        _stream(f"task:{task_id}"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
