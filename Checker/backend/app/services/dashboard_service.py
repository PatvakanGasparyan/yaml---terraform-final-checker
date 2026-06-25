"""
Dashboard analytics service.

Aggregates statistics, charts, and activity feed for dashboard widgets.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ActivityFeed,
    Project,
    SecurityScan,
    User,
    ValidationHistory,
    ValidationStatus,
)
from app.schemas import (
    ActivityItem,
    DashboardCharts,
    DashboardResponse,
    DashboardStats,
    TrendDataPoint,
)


class DashboardService:
    """
    Dashboard data aggregation service.

    Provides stats, trend charts, and recent activity for the UI.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db

    async def get_dashboard(self, user_id: int) -> DashboardResponse:
        """
        Get complete dashboard data for a user.

        Args:
            user_id: Current user ID.

        Returns:
            DashboardResponse with stats, charts, activity, recommendations.
        """
        stats = await self._get_stats(user_id)
        charts = await self._get_charts(user_id)
        activity = await self._get_recent_activity(user_id)
        recommendations = await self._get_ai_recommendations(user_id)

        return DashboardResponse(
            stats=stats,
            charts=charts,
            recent_activity=activity,
            ai_recommendations=recommendations,
        )

    async def _get_stats(self, user_id: int) -> DashboardStats:
        """Calculate dashboard widget statistics."""
        # Total scans by user
        total_result = await self.db.execute(
            select(func.count(ValidationHistory.id)).where(ValidationHistory.user_id == user_id)
        )
        total_scans = total_result.scalar() or 0

        failed_result = await self.db.execute(
            select(func.count(ValidationHistory.id)).where(
                ValidationHistory.user_id == user_id,
                ValidationHistory.status == ValidationStatus.FAILED,
            )
        )
        failed = failed_result.scalar() or 0

        success_result = await self.db.execute(
            select(func.count(ValidationHistory.id)).where(
                ValidationHistory.user_id == user_id,
                ValidationHistory.status == ValidationStatus.SUCCESS,
            )
        )
        successful = success_result.scalar() or 0

        security_result = await self.db.execute(
            select(func.count(SecurityScan.id)).join(ValidationHistory).where(
                ValidationHistory.user_id == user_id
            )
        )
        security_findings = security_result.scalar() or 0

        tf_result = await self.db.execute(
            select(func.count(Project.id)).where(
                Project.owner_id == user_id, Project.project_type.in_(["terraform", "mixed"])
            )
        )
        terraform_projects = tf_result.scalar() or 0

        yaml_result = await self.db.execute(
            select(func.count(Project.id)).where(
                Project.owner_id == user_id, Project.project_type.in_(["yaml", "mixed"])
            )
        )
        yaml_projects = yaml_result.scalar() or 0

        return DashboardStats(
            total_scans=total_scans,
            failed_validations=failed,
            successful_validations=successful,
            security_findings=security_findings,
            terraform_projects=terraform_projects,
            yaml_projects=yaml_projects,
            ai_recommendations=min(security_findings, 10),
        )

    async def _get_charts(self, user_id: int) -> DashboardCharts:
        """Generate chart data for last 30 days."""
        now = datetime.now(UTC)
        validation_trends = []
        security_trends = []

        for days_ago in range(29, -1, -1):
            date = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            day_start = now - timedelta(days=days_ago + 1)
            day_end = now - timedelta(days=days_ago)

            val_count = await self.db.execute(
                select(func.count(ValidationHistory.id)).where(
                    ValidationHistory.user_id == user_id,
                    ValidationHistory.created_at >= day_start,
                    ValidationHistory.created_at < day_end,
                )
            )
            validation_trends.append(
                TrendDataPoint(date=date, value=val_count.scalar() or 0, label="Validations")
            )

            sec_count = await self.db.execute(
                select(func.count(SecurityScan.id))
                .join(ValidationHistory)
                .where(
                    ValidationHistory.user_id == user_id,
                    SecurityScan.created_at >= day_start,
                    SecurityScan.created_at < day_end,
                )
            )
            security_trends.append(
                TrendDataPoint(date=date, value=sec_count.scalar() or 0, label="Security")
            )

        return DashboardCharts(
            validation_trends=validation_trends,
            security_trends=security_trends,
            repository_stats=[],
            scan_performance=validation_trends,
        )

    async def _get_recent_activity(self, user_id: int, limit: int = 10) -> list[ActivityItem]:
        """Get recent activity feed items."""
        result = await self.db.execute(
            select(ActivityFeed, User.username)
            .join(User, ActivityFeed.user_id == User.id)
            .where(ActivityFeed.user_id == user_id)
            .order_by(ActivityFeed.created_at.desc())
            .limit(limit)
        )

        items = []
        for activity, username in result.all():
            items.append(
                ActivityItem(
                    id=activity.id,
                    activity_type=activity.activity_type,
                    title=activity.title,
                    description=activity.description,
                    user_name=username,
                    created_at=activity.created_at,
                )
            )
        return items

    async def _get_ai_recommendations(self, user_id: int) -> list[str]:
        """Generate AI recommendations based on recent validation patterns."""
        recommendations = []

        # Check for repeated failures
        failed_result = await self.db.execute(
            select(func.count(ValidationHistory.id)).where(
                ValidationHistory.user_id == user_id,
                ValidationHistory.status == ValidationStatus.FAILED,
                ValidationHistory.created_at >= datetime.now(UTC) - timedelta(days=7),
            )
        )
        if (failed_result.scalar() or 0) > 3:
            recommendations.append(
                "Multiple validation failures detected this week. Review common error patterns."
            )

        sec_result = await self.db.execute(
            select(func.count(SecurityScan.id))
            .join(ValidationHistory)
            .where(
                ValidationHistory.user_id == user_id,
                SecurityScan.created_at >= datetime.now(UTC) - timedelta(days=7),
            )
        )
        if (sec_result.scalar() or 0) > 0:
            recommendations.append(
                "Security findings detected. Run security scans on all repositories."
            )

        if not recommendations:
            recommendations.append("All validations passing. Consider enabling automatic PR scans.")

        return recommendations
