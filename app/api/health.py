from fastapi import APIRouter
from app.workers.celery_app import celery_app

router = APIRouter()

@router.get("/worker")
def check_worker_health():
    """Check Celery worker availability and current load."""
    try:
        inspect = celery_app.control.inspect(timeout=3)
        ping = inspect.ping()
        if ping:
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            return {
                "status": "ok",
                "workers": list(ping.keys()),
                "active_tasks": sum(len(v) for v in active.values()),
                "reserved_tasks": sum(len(v) for v in reserved.values()),
            }
        return {"status": "down", "workers": []}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
