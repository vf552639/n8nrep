import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.config import settings

celery_app = Celery(
    "seo_generator", broker=settings.REDIS_URL, backend=settings.REDIS_URL, include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_concurrency=settings.CELERY_CONCURRENCY,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_SOFT_TIME_LIMIT,
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)


@worker_process_init.connect
def _configure_worker_logging(**_kwargs) -> None:
    os.makedirs("logs", exist_ok=True)
    from app.logging_config import configure_logging

    configure_logging(
        json_logs=settings.LOG_JSON,
        level=settings.LOG_LEVEL,
        log_file_path="logs/worker.log",
    )


celery_app.conf.beat_schedule = {
    "cleanup-stale-tasks-every-10min": {
        "task": "app.workers.tasks.cleanup_stale_tasks",
        "schedule": crontab(minute="*/10"),
    },
}
