"""
Celery application configuration.

Configures async task queue for validation jobs, webhooks,
scheduled scans, and notifications.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

# Create Celery app with Redis broker
celery_app = Celery(
    "yaml_terraform_validator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "automatic-backup": {
        "task": "app.workers.tasks.run_mysql_backup",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM UTC
    },
    "cleanup-old-validations": {
        "task": "app.workers.tasks.cleanup_old_validations",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Weekly Sunday 3 AM
    },
    "sync-github-repos": {
        "task": "app.workers.tasks.sync_github_repositories",
        "schedule": crontab(minute="*/30"),  # Every 30 minutes
    },
}
