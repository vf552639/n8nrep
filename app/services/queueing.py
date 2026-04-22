"""Enqueue Celery generation jobs and persist celery_task_id on Task."""

import logging

from sqlalchemy.orm import Session

from app.models.task import Task
from app.workers.tasks import process_generation_task

logger = logging.getLogger(__name__)


def enqueue_task_generation(db: Session, task: Task) -> str:
    res = process_generation_task.delay(str(task.id))
    task.celery_task_id = str(res.id)
    db.commit()
    return str(res.id)


def revoke_generation_celery_task(celery_task_id: str | None) -> None:
    if not celery_task_id or not str(celery_task_id).strip():
        return
    from app.workers.celery_app import celery_app

    try:
        celery_app.control.revoke(str(celery_task_id), terminate=True, signal="SIGTERM")
    except Exception as exc:
        logger.warning("Celery revoke failed for id=%s: %s", celery_task_id, exc)
