"""
Dashboard API endpoints.

Provides statistics, charts, and activity feed data.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_user_or_guest
from app.core.database import get_db
from app.models import User
from app.schemas import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Annotated[User, Depends(get_user_or_guest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardResponse:
    """
    Get complete dashboard data.

    Returns stats widgets, trend charts, recent activity, and AI recommendations.
    """
    service = DashboardService(db)
    return await service.get_dashboard(current_user.id)
