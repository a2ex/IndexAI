from celery import Celery
from celery.schedules import crontab
import sentry_sdk
from app.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment="production" if "railway" in settings.DATABASE_URL else "development",
    )

celery = Celery(
    "indexing_service",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.indexing_tasks",
        "app.tasks.verification_tasks",
        "app.tasks.credit_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_max_tasks_per_child=100,
)

celery.conf.task_routes = {
    "app.tasks.verification_tasks.*": {"queue": "verification"},
}

celery.conf.beat_schedule = {
    # Check URLs submitted <6h — every hour (fast detection)
    "check-fresh-urls": {
        "task": "app.tasks.verification_tasks.check_fresh_urls",
        "schedule": crontab(minute=0),
    },
    # Check URLs submitted <24h — every 6 hours
    "check-recent-urls": {
        "task": "app.tasks.verification_tasks.check_recent_urls",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    # Check URLs submitted 1-3 days ago — every 12 hours
    "check-pending-urls-1-3d": {
        "task": "app.tasks.verification_tasks.check_pending_urls",
        "schedule": crontab(minute=0, hour="*/12"),
        "kwargs": {"min_age_days": 1, "max_age_days": 3},
    },
    # Check URLs submitted 3-7 days ago — daily
    "check-pending-urls-3-7d": {
        "task": "app.tasks.verification_tasks.check_pending_urls",
        "schedule": crontab(minute=0, hour=6),
        "kwargs": {"min_age_days": 3, "max_age_days": 7},
    },
    # Final check at D+10 — daily
    "check-pending-urls-7-10d": {
        "task": "app.tasks.verification_tasks.check_pending_urls",
        "schedule": crontab(minute=0, hour=8),
        "kwargs": {"min_age_days": 7, "max_age_days": 10},
    },
    # Auto-refund non-indexed URLs after 14 days — daily
    "auto-recredit": {
        "task": "app.tasks.credit_tasks.auto_recredit_expired",
        "schedule": crontab(minute=0, hour=2),
    },
    # Reset service account quotas — midnight UTC
    "reset-sa-quotas": {
        "task": "app.tasks.indexing_tasks.reset_service_account_quotas",
        "schedule": crontab(minute=0, hour=0),
    },
    # Process pending URLs — every 10 minutes
    "process-pending-urls": {
        "task": "app.tasks.indexing_tasks.process_pending_urls",
        "schedule": 600.0,
    },
    # Process method queue (rate-limited, staggered) — every 2 minutes
    "process-method-queue": {
        "task": "app.tasks.indexing_tasks.process_method_queue",
        "schedule": 120.0,
    },
    # Daily email digest of indexed URLs — 9:00 UTC
    "send-daily-digest": {
        "task": "app.tasks.notification_tasks.send_daily_digest",
        "schedule": crontab(minute=0, hour=9),
    },
}
