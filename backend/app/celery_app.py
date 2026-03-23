from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "pineapple",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.timezone = settings.sched_tz
celery_app.conf.enable_utc = True
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.beat_schedule = {
    "check-expired-subscriptions": {
        "task": "app.tasks.check_expired_subscriptions",
        "schedule": 300.0,
    },
    "send-renewal-reminders": {
        "task": "app.tasks.send_renewal_reminders",
        "schedule": 3600.0,
    },
    "send-trial-activation-reminders": {
        "task": "app.tasks.send_trial_activation_reminders",
        "schedule": 86400.0,
    },
    "ingest-xray-access-logs": {
        "task": "app.tasks.ingest_xray_access_logs",
        "schedule": float(max(settings.vpn_access_log_poll_seconds, 30)),
    },
    "check-daily-data-limits": {
        "task": "app.tasks.check_daily_data_limits",
        "schedule": 600.0,
    },
    "cleanup-connection-logs": {
        "task": "app.tasks.cleanup_connection_logs",
        "schedule": 86400.0,
    },
    "send-my-nalog-daily-report": {
        "task": "app.tasks.send_my_nalog_daily_report",
        "schedule": crontab(hour=21, minute=5),
    },
}

import app.tasks  # noqa: E402,F401
