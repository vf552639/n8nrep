from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.site import Site
from app.models.task import Task

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    failed_tasks = db.query(Task).filter(Task.status == "failed").count()
    processing_tasks = db.query(Task).filter(Task.status == "processing").count()
    pending_tasks = db.query(Task).filter(Task.status == "pending").count()

    total_sites = db.query(Site).count()

    from app.config import settings

    cutoff = datetime.utcnow() - timedelta(days=30)
    cost_rows = (
        db.query(cast(Task.updated_at, Date).label("d"), func.coalesce(func.sum(Task.total_cost), 0.0))
        .filter(Task.status == "completed", Task.updated_at >= cutoff, Task.total_cost.isnot(None))
        .group_by("d")
        .order_by("d")
        .all()
    )
    cost_by_day = [{"date": str(r[0]), "cost": float(r[1] or 0)} for r in cost_rows]

    return {
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks,
            "processing": processing_tasks,
            "pending": pending_tasks,
        },
        "sites": total_sites,
        "sequential_mode": settings.SEQUENTIAL_MODE,
        "cost_by_day": cost_by_day,
    }


@router.get("/queue")
def get_queue_status():
    """
    Very basic queue status. For accurate info,
    one would query Redis or use Celery Inspector.
    """
    try:
        from app.workers.celery_app import celery_app

        i = celery_app.control.inspect()
        active = i.active()
        reserved = i.reserved()
        return {
            "celery_workers_online": bool(active),
            "active_tasks": active if active else {},
            "queued_tasks": reserved if reserved else {},
        }
    except Exception as e:
        return {"celery_workers_online": False, "error": str(e)}
