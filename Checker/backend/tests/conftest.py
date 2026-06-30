"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Configure test environment before any `app` package import.
_backend_root = Path(__file__).resolve().parents[1]
_test_data = _backend_root / ".pytest-data"
_test_data.mkdir(exist_ok=True)

_test_env = _test_data / "test.env"
_test_env.write_text(
    "\n".join(
        [
            "APP_ENV=development",
            "DEBUG=true",
            "SECRET_KEY=test-secret-key-for-pytest-only",
            "DB_ENGINE=sqlite",
            "SQLITE_PATH=.pytest-data/app.db",
            "REDIS_HOST=disabled",
            "OTEL_ENABLED=false",
        ]
    )
    + "\n",
    encoding="utf-8",
)
os.environ["ENV_FILE_PATH"] = str(_test_env)


@pytest.fixture
async def client() -> AsyncClient:
    """HTTP client with FastAPI lifespan enabled (DB init + guest user)."""
    from app.main import app

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
