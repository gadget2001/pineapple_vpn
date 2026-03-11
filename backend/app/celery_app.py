from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "pineapple",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.timezone = settings.sched_tz
celery_app.conf.enable_utc = True
celery_app.conf.beat_schedule = {
    "check-expired-subscriptions": {
        "task": "app.tasks.check_expired_subscriptions",
        "schedule": 300.0,
    },
    "send-renewal-reminders": {
        "task": "app.tasks.send_renewal_reminders",
        "schedule": 3600.0,
    },
    "cleanup-connection-logs": {
        "task": "app.tasks.cleanup_connection_logs",
        "schedule": 86400.0,
    },
}

import app.tasks  # noqa: E402,F401
