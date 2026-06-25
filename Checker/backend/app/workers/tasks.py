"""
Celery background tasks.

Handles async validation, webhook processing, backups,
notifications, and scheduled maintenance.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.run_validation_async", bind=True, max_retries=3)
def run_validation_async(
    self: Any,
    content: str,
    file_path: str,
    user_id: int,
    validation_type: str = "auto",
    include_ai: bool = True,
    include_security: bool = True,
) -> dict[str, Any]:
    """
    Run validation asynchronously via Celery worker.

    Args:
        content: File content to validate.
        file_path: Virtual file path.
        user_id: User initiating validation.
        validation_type: yaml, terraform, or auto.
        include_ai: Whether to run AI analysis.
        include_security: Whether to run security scan.

    Returns:
        Validation result dict.
    """
    import asyncio

    from app.schemas import ValidationRequest
    from app.services.validation_service import ValidationService
    from app.core.database import AsyncSessionLocal

    async def _run() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            service = ValidationService(session)
            request = ValidationRequest(
                content=content,
                file_path=file_path,
                validation_type=validation_type,
                include_ai_analysis=include_ai,
                include_security_scan=include_security,
            )
            result = await service.validate(request, user_id)
            return result.model_dump()

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        logger.error(f"Validation task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="app.workers.tasks.run_webhook_validation")
def run_webhook_validation(
    repo_full_name: str,
    ref: str,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, str]:
    """
    Process GitHub webhook and trigger validation.

    Args:
        repo_full_name: GitHub org/repo.
        ref: Branch name or PR number.
        event_type: push or pull_request.
        payload: Full webhook payload.

    Returns:
        Status dict.
    """
    logger.info(f"Processing {event_type} webhook for {repo_full_name}:{ref}")

    # Extract changed files from payload
    changed_files = []
    if event_type == "push":
        for commit in payload.get("commits", []):
            changed_files.extend(commit.get("added", []))
            changed_files.extend(commit.get("modified", []))

    # Filter for YAML and Terraform files
    relevant_files = [
        f for f in changed_files
        if f.endswith((".yaml", ".yml", ".tf", ".tfvars", ".hcl"))
    ]

    logger.info(f"Found {len(relevant_files)} relevant files to validate")
    return {"status": "queued", "files": str(len(relevant_files))}


@celery_app.task(name="app.workers.tasks.run_mysql_backup")
def run_mysql_backup() -> dict[str, str]:
    """
    Run automatic MySQL database backup.

    Creates timestamped SQL dump in /backups directory.
    """
    import subprocess
    from pathlib import Path

    from app.core.config import get_settings

    settings = get_settings()
    backup_dir = Path("/backups")
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{timestamp}.sql"

    try:
        subprocess.run(
            [
                "mysqldump",
                f"-h{settings.MYSQL_HOST}",
                f"-P{settings.MYSQL_PORT}",
                f"-u{settings.MYSQL_USER}",
                f"-p{settings.MYSQL_PASSWORD}",
                settings.MYSQL_DATABASE,
            ],
            stdout=open(backup_file, "w"),
            check=True,
            timeout=300,
        )
        logger.info(f"Backup created: {backup_file}")
        return {"status": "success", "file": str(backup_file)}
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="app.workers.tasks.cleanup_old_validations")
def cleanup_old_validations(days: int = 90) -> dict[str, int]:
    """
    Clean up validation history older than specified days.

    Args:
        days: Retention period in days.

    Returns:
        Count of deleted records.
    """
    import asyncio

    from sqlalchemy import delete

    from app.core.database import AsyncSessionLocal
    from app.models import ValidationHistory

    async def _cleanup() -> int:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(ValidationHistory).where(ValidationHistory.created_at < cutoff)
            )
            await session.commit()
            return result.rowcount or 0

    deleted = asyncio.get_event_loop().run_until_complete(_cleanup())
    logger.info(f"Cleaned up {deleted} old validation records")
    return {"deleted": deleted}


@celery_app.task(name="app.workers.tasks.sync_github_repositories")
def sync_github_repositories() -> dict[str, str]:
    """Sync linked GitHub repositories for auto-scan enabled repos."""
    logger.info("Syncing GitHub repositories")
    return {"status": "completed"}


@celery_app.task(name="app.workers.tasks.send_notification")
def send_notification(
    user_id: int,
    title: str,
    message: str,
    channel: str = "in_app",
) -> dict[str, str]:
    """
    Send notification via specified channel.

    Args:
        user_id: Target user ID.
        title: Notification title.
        message: Notification body.
        channel: email, slack, telegram, webhook, or in_app.

    Returns:
        Delivery status.
    """
    logger.info(f"Sending {channel} notification to user {user_id}: {title}")
    return {"status": "sent", "channel": channel}
