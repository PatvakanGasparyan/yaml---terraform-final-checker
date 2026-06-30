"""
Validation API endpoints.

Handles YAML/Terraform validation, history search, and export.
"""

import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_user_or_guest
from app.core.database import get_db
from app.models import User, ValidationHistory
from app.schemas import (
    PaginatedResponse,
    ValidationHistoryResponse,
    ValidationRequest,
    ValidationResponse,
)
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/validations", tags=["Validations"])


@router.post("/run", response_model=ValidationResponse)
async def run_validation(
    request: ValidationRequest,
    current_user: Annotated[User, Depends(get_user_or_guest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ValidationResponse:
    """
    Run validation on YAML or Terraform content.

    Performs syntax validation, security scanning, and optional AI analysis.
    """
    service = ValidationService(db)
    return await service.validate(request, current_user.id)


@router.get("/history", response_model=PaginatedResponse)
async def get_validation_history(
    current_user: Annotated[User, Depends(get_user_or_guest)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: int | None = None,
    status_filter: str | None = Query(None, alias="status"),
    validation_type: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> PaginatedResponse:
    """
    Search and filter validation history.

    Supports pagination, sorting, and text search on summary/commit.
    """
    query = select(ValidationHistory).where(ValidationHistory.user_id == current_user.id)

    if project_id:
        query = query.where(ValidationHistory.project_id == project_id)
    if status_filter:
        query = query.where(ValidationHistory.status == status_filter)
    if validation_type:
        query = query.where(ValidationHistory.validation_type == validation_type)
    if search:
        query = query.where(ValidationHistory.summary.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sort and paginate
    sort_column = getattr(ValidationHistory, sort_by, ValidationHistory.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[
            ValidationHistoryResponse(
                id=v.id,
                validation_type=v.validation_type,
                status=v.status,
                branch=v.branch,
                commit_sha=v.commit_sha,
                error_count=v.error_count,
                warning_count=v.warning_count,
                security_findings_count=v.security_findings_count,
                duration_ms=v.duration_ms,
                summary=v.summary,
                created_at=v.created_at,
            ).model_dump()
            for v in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{validation_id}", response_model=ValidationHistoryResponse)
async def get_validation(
    validation_id: int,
    current_user: Annotated[User, Depends(get_user_or_guest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ValidationHistoryResponse:
    """Get single validation history record by ID."""
    result = await db.execute(
        select(ValidationHistory).where(
            ValidationHistory.id == validation_id,
            ValidationHistory.user_id == current_user.id,
        )
    )
    validation = result.scalar_one_or_none()
    if not validation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation not found")

    return ValidationHistoryResponse(
        id=validation.id,
        validation_type=validation.validation_type,
        status=validation.status,
        branch=validation.branch,
        commit_sha=validation.commit_sha,
        error_count=validation.error_count,
        warning_count=validation.warning_count,
        security_findings_count=validation.security_findings_count,
        duration_ms=validation.duration_ms,
        summary=validation.summary,
        created_at=validation.created_at,
    )
