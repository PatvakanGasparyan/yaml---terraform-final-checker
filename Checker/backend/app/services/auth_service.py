"""
Authentication and user management service.

Handles registration, login, password reset, email verification, and MFA.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_mfa_secret,
    get_mfa_provisioning_uri,
    get_password_hash,
    verify_mfa_token,
    verify_password,
)
from app.models import Role, User
from app.schemas import TokenResponse, UserCreate, UserLogin, UserResponse

settings = get_settings()


class AuthService:
    """
    Authentication service for user registration, login, and MFA.

    Manages JWT token generation and user credential validation.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize with database session."""
        self.db = db

    async def register(self, user_data: UserCreate) -> UserResponse:
        """
        Register a new user account.

        Args:
            user_data: Registration payload with email, username, password.

        Returns:
            Created user profile.

        Raises:
            ValueError: If email or username already exists.
        """
        # Check existing user
        existing = await self.db.execute(
            select(User).where(
                (User.email == user_data.email) | (User.username == user_data.username)
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email or username already registered")

        # Create user with hashed password
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            preferred_language=user_data.preferred_language,
        )
        self.db.add(user)
        await self.db.flush()

        # Assign default developer role
        role_result = await self.db.execute(select(Role).where(Role.name == "developer"))
        role = role_result.scalar_one_or_none()
        if role:
            user.roles.append(role)

        await self.db.commit()
        await self.db.refresh(user, ["roles"])

        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            mfa_enabled=user.mfa_enabled,
            avatar_url=user.avatar_url,
            preferred_language=user.preferred_language,
            roles=[r.name for r in user.roles],
            created_at=user.created_at,
        )

    async def login(self, credentials: UserLogin) -> TokenResponse:
        """
        Authenticate user and return JWT tokens.

        Args:
            credentials: Email, password, and optional MFA token.

        Returns:
            Access and refresh JWT tokens.

        Raises:
            ValueError: If credentials are invalid or MFA required/failed.
        """
        result = await self.db.execute(
            select(User).options(selectinload(User.roles)).where(User.email == credentials.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(credentials.password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        # MFA verification
        if user.mfa_enabled:
            if not credentials.mfa_token:
                raise ValueError("MFA token required")
            if not user.mfa_secret or not verify_mfa_token(user.mfa_secret, credentials.mfa_token):
                raise ValueError("Invalid MFA token")

        # Update last login
        user.last_login = datetime.now(UTC)
        await self.db.commit()

        roles = [role.name for role in user.roles]
        access_token = create_access_token(user.id, extra_claims={"roles": roles})
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def setup_mfa(self, user_id: int) -> dict[str, str]:
        """
        Initialize MFA setup for a user.

        Args:
            user_id: User ID.

        Returns:
            Dict with secret and provisioning URI for QR code.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        secret = generate_mfa_secret()
        user.mfa_secret = secret
        await self.db.commit()

        return {
            "secret": secret,
            "provisioning_uri": get_mfa_provisioning_uri(secret, user.email),
        }

    async def enable_mfa(self, user_id: int, token: str) -> bool:
        """
        Enable MFA after verifying TOTP token.

        Args:
            user_id: User ID.
            token: 6-digit TOTP code.

        Returns:
            True if MFA enabled successfully.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.mfa_secret:
            raise ValueError("MFA not initialized")

        if not verify_mfa_token(user.mfa_secret, token):
            raise ValueError("Invalid MFA token")

        user.mfa_enabled = True
        await self.db.commit()
        return True

    async def seed_default_roles(self) -> None:
        """Seed default RBAC roles and permissions if not exist."""
        default_roles = [
            ("admin", "Full platform access"),
            ("manager", "Team and project management"),
            ("developer", "Create and run validations"),
            ("viewer", "Read-only access"),
        ]

        for name, description in default_roles:
            existing = await self.db.execute(select(Role).where(Role.name == name))
            if not existing.scalar_one_or_none():
                self.db.add(Role(name=name, description=description))

        await self.db.commit()
