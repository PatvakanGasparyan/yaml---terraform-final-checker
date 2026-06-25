"""
Database connection and session management.

Provides async SQLAlchemy engine, session factory, and dependency
injection helper for FastAPI route handlers.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# Async engine with connection pooling for production workloads
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Session factory - creates new AsyncSession instances per request
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for all ORM models.

    All database models inherit from this class to share metadata
    and enable Alembic auto-generation of migrations.
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.

    Ensures the session is properly closed after the request completes,
    even if an exception occurs during request processing.

    Yields:
        AsyncSession: SQLAlchemy async session bound to the request lifecycle.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database tables on application startup.

    Creates all tables defined in ORM models if they do not exist.
    In production, Alembic migrations should be used instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Allow anonymous validations; column type must match projects.id (UNSIGNED)
        try:
            await conn.execute(
                text(
                    "ALTER TABLE validation_history MODIFY COLUMN project_id INT UNSIGNED NULL"
                )
            )
        except Exception:
            # Column already nullable or table created from current schema
            pass
