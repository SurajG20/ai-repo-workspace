from __future__ import annotations

from celery import Celery

from .config import settings

app = Celery(
    "aiworkspace",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    "dispatch-pending-jobs": {
        "task": "dispatch_pending_jobs",
        "schedule": 5.0,
    },
}
