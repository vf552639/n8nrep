from fastapi import APIRouter, Query

from app.config import settings

router = APIRouter()


@router.get("/worker")
def check_worker_health():
    if settings.DESKTOP_MODE:
        from app.services.project_runner import get_runner_status
        return get_runner_status()
    # Web mode: Celery inspect
    from app.workers.celery_app import celery_app

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


@router.get("/serp")
def serp_health_check(force: bool = Query(False, description="Bypass 5-minute cache")):
    """
    Check SERP providers availability.
    Results are cached for 5 minutes unless force=true.
    """
    from app.services.serp import get_serp_health

    return get_serp_health(force_refresh=force)
