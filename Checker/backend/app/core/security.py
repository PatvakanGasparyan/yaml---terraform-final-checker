"""
Security utilities for authentication and authorization.

Handles password hashing, JWT token creation/validation, MFA (TOTP),
and API key generation/verification.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# bcrypt password hashing context with automatic deprecation handling
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against its bcrypt hash.

    Args:
        plain_password: User-provided password.
        hashed_password: Stored bcrypt hash from database.

    Returns:
        True if password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain-text password to hash.

    Returns:
        Bcrypt hash string safe for database storage.
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a JWT access token for authenticated API access.

    Args:
        subject: User ID or identifier to embed in token.
        expires_delta: Optional custom expiration duration.
        extra_claims: Additional JWT payload fields (roles, permissions).

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    """
    Create a long-lived JWT refresh token.

    Args:
        subject: User ID to embed in token.

    Returns:
        Encoded JWT refresh token string.
    """
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT string from Authorization header.

    Returns:
        Decoded payload dict, or None if token is invalid/expired.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key pair (public prefix + secret).

    Returns:
        Tuple of (full_key_for_user, hashed_key_for_storage).
        Format: ytv_<prefix>_<secret>
    """
    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    full_key = f"ytv_{prefix}_{secret}"
    hashed = get_password_hash(full_key)
    return full_key, hashed


def generate_mfa_secret() -> str:
    """
    Generate a TOTP secret for MFA enrollment.

    Returns:
        Base32-encoded secret for authenticator apps.
    """
    return pyotp.random_base32()


def verify_mfa_token(secret: str, token: str) -> bool:
    """
    Verify a TOTP token against the user's MFA secret.

    Args:
        secret: User's TOTP secret from database.
        token: 6-digit code from authenticator app.

    Returns:
        True if token is valid within the allowed time window.
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)


def get_mfa_provisioning_uri(secret: str, email: str) -> str:
    """
    Generate otpauth URI for QR code generation during MFA setup.

    Args:
        secret: TOTP secret.
        email: User email for label in authenticator app.

    Returns:
        otpauth:// URI string for QR code rendering.
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.APP_NAME)
