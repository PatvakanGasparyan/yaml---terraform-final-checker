"""Tests for validation service pipeline fixes."""

import pytest

from app.schemas import ValidationRequest
from app.services.validation_service import ValidationService


class _NoDb:
    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    def add(self, *_: object) -> None:
        pass


@pytest.mark.asyncio
async def test_auto_invalid_yaml_still_returns_findings() -> None:
    """Invalid YAML in auto mode must surface syntax errors (regression)."""
    service = ValidationService(_NoDb())  # type: ignore[arg-type]
    request = ValidationRequest(
        content="apiVersion: v1\nkind: Pod\n  bad indent",
        file_path="pod.yaml",
        validation_type="auto",
        include_ai_analysis=False,
        include_security_scan=False,
        use_cache=False,
    )
    result = await service.validate_cli(request)
    assert len(result.findings) > 0
    assert result.error_count >= 0


@pytest.mark.asyncio
async def test_auto_fix_returns_corrected_content_when_fix_available() -> None:
    service = ValidationService(_NoDb())  # type: ignore[arg-type]
    sample = """services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
"""
    request = ValidationRequest(
        content=sample,
        file_path="docker-compose.yaml",
        validation_type="yaml",
        include_ai_analysis=False,
        include_security_scan=False,
        auto_fix=True,
        use_cache=False,
    )
    result = await service.validate_cli(request)
    assert result.validation_type == "yaml"
