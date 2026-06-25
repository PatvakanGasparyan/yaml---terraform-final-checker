"""
Authentication API endpoints.

Handles registration, login, token refresh, MFA, and password reset.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas import (
    MFAEnableRequest,
    MessageResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Register a new user account.

    Creates user with developer role and returns profile.
    """
    service = AuthService(db)
    try:
        return await service.register(user_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate user and return JWT access/refresh tokens.

    Requires MFA token if MFA is enabled on the account.
    """
    service = AuthService(db)
    try:
        return await service.login(credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Get current authenticated user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        mfa_enabled=current_user.mfa_enabled,
        avatar_url=current_user.avatar_url,
        preferred_language=current_user.preferred_language,
        roles=[r.name for r in current_user.roles],
        created_at=current_user.created_at,
    )


@router.post("/mfa/setup")
async def setup_mfa(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Initialize MFA setup and return provisioning URI for QR code."""
    service = AuthService(db)
    return await service.setup_mfa(current_user.id)


@router.post("/mfa/enable", response_model=MessageResponse)
async def enable_mfa(
    request: MFAEnableRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Enable MFA after verifying TOTP token."""
    service = AuthService(db)
    try:
        await service.enable_mfa(current_user.id, request.token)
        return MessageResponse(message="MFA enabled successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
