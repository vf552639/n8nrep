from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "seo_generator",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.workers.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_concurrency=settings.CELERY_CONCURRENCY,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)

celery_app.conf.beat_schedule = {
    'cleanup-stale-tasks-every-hour': {
        'task': 'app.workers.tasks.cleanup_stale_tasks',
        'schedule': crontab(minute=0, hour='*'), # every hour
    },
}
