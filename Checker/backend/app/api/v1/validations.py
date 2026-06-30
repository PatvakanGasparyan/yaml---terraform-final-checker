"""
Validation API endpoints.

Handles YAML/Terraform validation, history search, detail retrieval, and export.
"""

import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_user_or_guest
from app.core.database import get_db
from app.core.limiter import limiter
from app.models import User, ValidationHistory
from app.reporting.formats import ReportFormat, generate_report
from app.schemas import (
    PaginatedResponse,
    ValidationDetailResponse,
    ValidationHistoryResponse,
    ValidationRequest,
    ValidationResponse,
)
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/validations", tags=["Validations"])


@router.post("/run", response_model=ValidationResponse)
@limiter.limit("30/minute")
async def run_validation(
    request: Request,
    body: ValidationRequest,
    current_user: Annotated[User, Depends(get_user_or_guest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ValidationResponse:
    """
    Run validation on YAML or Terraform content.

    Set `auto_fix=true` for --fix mode (returns corrected_content when fixes apply).
    """
    service = ValidationService(db)
    return await service.validate(body, current_user.id)


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
    """Search and filter validation history with pagination."""
    query = select(ValidationHistory).where(ValidationHistory.user_id == current_user.id)

    if project_id:
        query = query.where(ValidationHistory.project_id == project_id)
    if status_filter:
        query = query.where(ValidationHistory.status == status_filter)
    if validation_type:
        query = query.where(ValidationHistory.validation_type == validation_type)
    if search:
        query = query.where(ValidationHistory.summary.ilike(f"%{search}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    sort_column = getattr(ValidationHistory, sort_by, ValidationHistory.created_at)
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())
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


@router.get("/{validation_id}/export")
async def export_validation(
    validation_id: int,
    current_user: Annotated[User, Depends(get_user_or_guest)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: ReportFormat = Query(ReportFormat.JSON, alias="format"),
) -> Response:
    """Export validation results as JSON, YAML, Markdown, HTML, SARIF, or JUnit."""
    service = ValidationService(db)
    detail = await service.get_validation_detail(validation_id, current_user.id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation not found")

    body, media_type = generate_report(
        ValidationResponse.model_validate(detail.model_dump()),
        format,
    )
    ext = format.value
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="validation-{validation_id}.{ext}"'},
    )


@router.get("/{validation_id}", response_model=ValidationDetailResponse)
async def get_validation(
    validation_id: int,
    current_user: Annotated[User, Depends(get_user_or_guest)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ValidationDetailResponse:
    """Get full validation record with findings, security results, and AI explanations."""
    service = ValidationService(db)
    detail = await service.get_validation_detail(validation_id, current_user.id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Validation not found")
    return detail
