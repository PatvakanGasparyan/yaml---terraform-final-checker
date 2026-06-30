"""Tests for report format generators."""

from app.reporting.formats import ReportFormat, generate_report
from app.schemas import ValidationResponse, ValidationStatus


def _sample_result() -> ValidationResponse:
    return ValidationResponse(
        validation_id=1,
        status=ValidationStatus.SUCCESS,
        validation_type="yaml",
        duration_ms=42,
        error_count=0,
        warning_count=1,
        security_findings_count=0,
        findings=[],
        summary="1 warning(s)",
    )


def test_json_report() -> None:
    body, mime = generate_report(_sample_result(), ReportFormat.JSON)
    assert mime == "application/json"
    assert "validation_id" in body


def test_sarif_report() -> None:
    body, mime = generate_report(_sample_result(), ReportFormat.SARIF)
    assert mime == "application/sarif+json"
    assert "2.1.0" in body


def test_junit_report() -> None:
    body, mime = generate_report(_sample_result(), ReportFormat.JUNIT)
    assert mime == "application/xml"
    assert "testsuite" in body
