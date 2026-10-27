from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "effortless",
    broker=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.adapters.tasks.payment_retry.process_payment_retry": {
            "queue": "payment-retries",
        },
    },
)

celery_app.autodiscover_tasks(
    ["app.adapters.tasks"],
)
