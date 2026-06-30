"""
Validation orchestration service.

Coordinates YAML/Terraform validation, security scanning,
AI analysis, plugin hooks, caching, and persistence.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analyzer import AIAnalyzer
from app.cache.validation_cache import build_cache_key, get_validation_cache
from app.core.config import get_settings
from app.models import (
    AIExplanation,
    SecurityScan,
    SeverityLevel as DBSeverity,
    ValidationHistory,
    ValidationResult,
    ValidationStatus,
)
from app.plugins.registry import get_plugin_registry
from app.schemas import (
    LineExplanation,
    SecurityFinding,
    SeverityLevel,
    ValidationDetailResponse,
    ValidationFinding,
    ValidationRequest,
    ValidationResponse,
    ValidationStatus as SchemaValidationStatus,
)
from app.security.scanner import SecurityScanner
from app.validators.terraform_validator import TerraformValidator
from app.validators.yaml_validator import YamlValidator

logger = logging.getLogger(__name__)
settings = get_settings()


class ValidationService:
    """
    Main validation orchestration service.

    Runs validation pipeline: detect type → validate → security scan → AI → persist.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ai_analyzer = AIAnalyzer()

    async def validate_cli(self, request: ValidationRequest) -> ValidationResponse:
        """Run validation without database persistence (CLI mode)."""
        return await self._run_pipeline(request, user_id=0, persist=False)

    async def validate(self, request: ValidationRequest, user_id: int) -> ValidationResponse:
        """Execute full validation pipeline with optional DB persistence."""
        return await self._run_pipeline(request, user_id=user_id, persist=True)

    async def get_validation_detail(
        self,
        validation_id: int,
        user_id: int,
    ) -> ValidationDetailResponse | None:
        """Load full validation results from database."""
        result = await self.db.execute(
            select(ValidationHistory).where(
                ValidationHistory.id == validation_id,
                ValidationHistory.user_id == user_id,
            )
        )
        history = result.scalar_one_or_none()
        if not history:
            return None

        findings_q = await self.db.execute(
            select(ValidationResult).where(ValidationResult.validation_id == validation_id)
        )
        scans_q = await self.db.execute(
            select(SecurityScan).where(SecurityScan.validation_id == validation_id)
        )
        ai_q = await self.db.execute(
            select(AIExplanation).where(AIExplanation.validation_id == validation_id)
        )

        db_to_schema = {
            DBSeverity.CRITICAL: SeverityLevel.CRITICAL,
            DBSeverity.HIGH: SeverityLevel.HIGH,
            DBSeverity.MEDIUM: SeverityLevel.MEDIUM,
            DBSeverity.LOW: SeverityLevel.LOW,
            DBSeverity.INFORMATIONAL: SeverityLevel.INFORMATIONAL,
        }

        findings = [
            ValidationFinding(
                file_path=f.file_path,
                line_number=f.line_number,
                column_number=f.column_number,
                rule_id=f.rule_id,
                severity=db_to_schema.get(f.severity, SeverityLevel.INFORMATIONAL),
                category=f.category,
                message=f.message,
                original_code=f.original_code,
                corrected_code=f.corrected_code,
                correction_reason=f.correction_reason,
                impact=f.impact,
            )
            for f in findings_q.scalars().all()
        ]

        security_findings = [
            SecurityFinding(
                scanner=s.scanner,
                rule_id=s.rule_id,
                severity=db_to_schema.get(s.severity, SeverityLevel.MEDIUM),
                title=s.title,
                description=s.description,
                file_path=s.file_path,
                line_number=s.line_number,
                resource=s.resource,
                remediation=s.remediation,
            )
            for s in scans_q.scalars().all()
        ]

        ai_explanations = [
            LineExplanation(
                line_number=e.line_number,
                code=e.code,
                explanation=e.explanation,
                risk_level=db_to_schema.get(e.risk_level, SeverityLevel.INFORMATIONAL),
                recommendation=e.recommendation,
            )
            for e in ai_q.scalars().all()
        ]

        return ValidationDetailResponse(
            validation_id=history.id,
            status=SchemaValidationStatus(history.status.value),
            validation_type=history.validation_type,
            duration_ms=history.duration_ms or 0,
            error_count=history.error_count,
            warning_count=history.warning_count,
            security_findings_count=history.security_findings_count,
            findings=findings,
            security_findings=security_findings,
            ai_explanations=ai_explanations,
            corrected_content=None,
            summary=history.summary,
            branch=history.branch,
            commit_sha=history.commit_sha,
            created_at=history.created_at,
        )

    async def _run_pipeline(
        self,
        request: ValidationRequest,
        user_id: int,
        persist: bool,
    ) -> ValidationResponse:
        start_time = time.time()
        validation_type = self._detect_validation_type(request)

        cache_key = build_cache_key(
            request.content,
            request.file_path,
            validation_type,
            request.include_ai_analysis,
            request.include_security_scan,
            request.auto_fix,
        )
        if request.use_cache and settings.VALIDATION_CACHE_ENABLED:
            cached = get_validation_cache().get(cache_key)
            if cached:
                logger.info("Validation cache hit file=%s", request.file_path)
                return ValidationResponse.model_validate(cached)

        history: ValidationHistory | None = None
        if persist:
            history = ValidationHistory(
                project_id=request.project_id,
                repository_id=request.repository_id,
                user_id=user_id,
                validation_type=validation_type,
                status=ValidationStatus.RUNNING,
                branch=request.branch,
            )
            self.db.add(history)
            await self.db.flush()

        findings: list[ValidationFinding] = []
        security_findings: list[SecurityFinding] = []
        ai_explanations: list[LineExplanation] = []
        corrected_content: str | None = None
        metadata: dict[str, Any] = {}
        file_path_for_ai = request.file_path

        try:
            if validation_type in ("yaml", "auto"):
                yaml_result = YamlValidator(request.content, request.file_path).validate_all()
                findings.extend(yaml_result.findings)
                metadata.update(yaml_result.metadata)
                if yaml_result.file_type != "generic":
                    validation_type = "yaml"

            if validation_type in ("terraform", "auto") or request.file_path.endswith(
                (".tf", ".hcl", ".tfvars")
            ):
                tf_result = TerraformValidator(request.content, request.file_path).validate_all()
                findings.extend(tf_result.findings)
                metadata.update(tf_result.metadata)
                validation_type = "terraform"
                if tf_result.formatted_content:
                    corrected_content = tf_result.formatted_content

            plugin_findings = get_plugin_registry().run_all(
                request.content, request.file_path, validation_type
            )
            findings.extend(plugin_findings)

            if request.include_security_scan:
                scan_result = SecurityScanner(
                    request.content, request.file_path, validation_type
                ).scan_all()
                security_findings = scan_result.findings
                metadata["scanners_run"] = scan_result.scanners_run

            if request.include_ai_analysis:
                language = "terraform" if validation_type == "terraform" else "yaml"
                ai_explanations = await self.ai_analyzer.explain_lines(
                    request.content, file_path_for_ai, language
                )
                corrected, findings = await self.ai_analyzer.generate_fixes(
                    request.content, findings, language
                )
                if corrected:
                    corrected_content = corrected

            if request.auto_fix and corrected_content is None:
                corrected_content = self._apply_inline_fixes(request.content, findings)

            error_count = sum(
                1 for f in findings if f.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH)
            )
            warning_count = sum(
                1 for f in findings if f.severity in (SeverityLevel.MEDIUM, SeverityLevel.LOW)
            )

            if error_count > 0:
                status = ValidationStatus.FAILED
            elif warning_count > 0 or security_findings:
                status = ValidationStatus.WARNING
            else:
                status = ValidationStatus.SUCCESS

            duration_ms = int((time.time() - start_time) * 1000)
            summary = self._generate_summary(error_count, warning_count, len(security_findings))

            response = ValidationResponse(
                validation_id=history.id if history else 0,
                status=SchemaValidationStatus(status.value),
                validation_type=validation_type,
                duration_ms=duration_ms,
                error_count=error_count,
                warning_count=warning_count,
                security_findings_count=len(security_findings),
                findings=findings,
                security_findings=security_findings,
                ai_explanations=ai_explanations,
                corrected_content=corrected_content,
                summary=summary,
                metadata=metadata,
            )

            if request.use_cache and settings.VALIDATION_CACHE_ENABLED:
                get_validation_cache().set(cache_key, response.model_dump(mode="json"))

            if persist and history:
                history.status = status
                history.validation_type = validation_type
                history.duration_ms = duration_ms
                history.error_count = error_count
                history.warning_count = warning_count
                history.security_findings_count = len(security_findings)
                history.summary = summary
                await self._persist_results(
                    history, findings, security_findings, ai_explanations, file_path_for_ai
                )
                await self.db.commit()
                response.validation_id = history.id

            return response

        except Exception as exc:
            logger.exception("Validation pipeline failed")
            if persist and history:
                history.status = ValidationStatus.FAILED
                history.summary = f"Validation failed: {exc}"
                await self.db.commit()
            raise

    @staticmethod
    def _apply_inline_fixes(content: str, findings: list[ValidationFinding]) -> str | None:
        lines = content.splitlines()
        changed = False
        for finding in findings:
            if finding.corrected_code and finding.line_number and finding.original_code:
                idx = finding.line_number - 1
                if 0 <= idx < len(lines) and finding.original_code.strip() in lines[idx]:
                    lines[idx] = finding.corrected_code
                    changed = True
        return "\n".join(lines) if changed else None

    def _detect_validation_type(self, request: ValidationRequest) -> str:
        if request.validation_type != "auto":
            return request.validation_type
        path = request.file_path.lower()
        if path.endswith((".tf", ".tfvars", ".hcl")):
            return "terraform"
        if path.endswith((".yaml", ".yml")):
            return "yaml"
        if "resource " in request.content and "provider " in request.content:
            return "terraform"
        return "yaml"

    async def _persist_results(
        self,
        history: ValidationHistory,
        findings: list[ValidationFinding],
        security_findings: list[SecurityFinding],
        ai_explanations: list[LineExplanation],
        file_path: str,
    ) -> None:
        severity_map = {
            SeverityLevel.CRITICAL: DBSeverity.CRITICAL,
            SeverityLevel.HIGH: DBSeverity.HIGH,
            SeverityLevel.MEDIUM: DBSeverity.MEDIUM,
            SeverityLevel.LOW: DBSeverity.LOW,
            SeverityLevel.INFORMATIONAL: DBSeverity.INFORMATIONAL,
        }

        for finding in findings:
            self.db.add(
                ValidationResult(
                    validation_id=history.id,
                    file_path=finding.file_path,
                    line_number=finding.line_number,
                    column_number=finding.column_number,
                    rule_id=finding.rule_id,
                    severity=severity_map.get(finding.severity, DBSeverity.INFORMATIONAL),
                    category=finding.category,
                    message=finding.message,
                    original_code=finding.original_code,
                    corrected_code=finding.corrected_code,
                    correction_reason=finding.correction_reason,
                    impact=finding.impact,
                )
            )

        for sf in security_findings:
            self.db.add(
                SecurityScan(
                    validation_id=history.id,
                    scanner=sf.scanner,
                    rule_id=sf.rule_id,
                    severity=severity_map.get(sf.severity, DBSeverity.MEDIUM),
                    title=sf.title,
                    description=sf.description,
                    file_path=sf.file_path,
                    line_number=sf.line_number,
                    resource=sf.resource,
                    remediation=sf.remediation,
                )
            )

        for exp in ai_explanations:
            self.db.add(
                AIExplanation(
                    validation_id=history.id,
                    file_path=file_path,
                    line_number=exp.line_number,
                    code=exp.code,
                    explanation=exp.explanation,
                    risk_level=severity_map.get(exp.risk_level, DBSeverity.INFORMATIONAL),
                    recommendation=exp.recommendation,
                )
            )

    @staticmethod
    def _generate_summary(errors: int, warnings: int, security: int) -> str:
        parts = []
        if errors:
            parts.append(f"{errors} error(s)")
        if warnings:
            parts.append(f"{warnings} warning(s)")
        if security:
            parts.append(f"{security} security finding(s)")
        return ", ".join(parts) if parts else "All checks passed"
