"""
FastAPI dependency injection helpers.

Provides current user extraction from JWT, permission checks,
and API key authentication.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token, verify_password
from app.models import ApiKey, User

# Bearer token security scheme for Swagger UI
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Extract and validate the current user from JWT Bearer token.

    Raises 401 if token is missing, invalid, or user not found/inactive.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == int(user_id), User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Optional auth - returns None instead of raising 401."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_guest_user(db: AsyncSession) -> User:
    """
    Return the shared guest account for unauthenticated public access.

    Created on first use if it does not exist.
    """
    from app.core.security import get_password_hash

    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.username == "guest")
    )
    guest = result.scalar_one_or_none()

    if guest is None:
        guest = User(
            email="guest@local",
            username="guest",
            hashed_password=get_password_hash("guest-not-used"),
            full_name="Guest",
            is_active=True,
            is_verified=True,
        )
        db.add(guest)
        await db.flush()

    return guest


async def get_user_or_guest(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Resolve the current user from JWT/API key, or fall back to the guest account.

    Enables public access without registration or login.
    """
    user = await get_current_user_optional(credentials, db)
    if user is not None:
        return user
    return await get_guest_user(db)


async def get_api_key_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Authenticate via API key (ytv_prefix_secret format).

    Falls back to JWT if Bearer token is not an API key.
    """
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required")

    token = credentials.credentials

    # Check if it's an API key format
    if token.startswith("ytv_"):
        result = await db.execute(
            select(ApiKey)
            .options(selectinload(ApiKey.user))
            .where(ApiKey.is_active.is_(True), ApiKey.key_prefix == token.split("_")[1])
        )
        api_keys = result.scalars().all()

        for api_key in api_keys:
            if verify_password(token, api_key.hashed_key):
                return api_key.user

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Fall back to JWT
    return await get_current_user(credentials, db)


def require_role(*roles: str):
    """
    Dependency factory that requires user to have one of the specified roles.

    Usage: Depends(require_role("admin", "manager"))
    """

    async def role_checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        user_roles = {role.name for role in user.roles}
        if not user_roles.intersection(set(roles)) and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return user

    return role_checker
