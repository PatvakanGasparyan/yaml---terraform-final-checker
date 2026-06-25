"""
Validation orchestration service.

Coordinates YAML/Terraform validation, security scanning,
AI analysis, and persistence to database.
"""

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analyzer import AIAnalyzer
from app.models import (
    AIExplanation,
    SecurityScan,
    SeverityLevel as DBSeverity,
    ValidationHistory,
    ValidationResult,
    ValidationStatus,
)
from app.schemas import (
    LineExplanation,
    SecurityFinding,
    SeverityLevel,
    ValidationFinding,
    ValidationRequest,
    ValidationResponse,
    ValidationStatus as SchemaValidationStatus,
)
from app.security.scanner import SecurityScanner
from app.validators.terraform_validator import TerraformValidator
from app.validators.yaml_validator import YamlValidator


class ValidationService:
    """
    Main validation orchestration service.

    Runs validation pipeline: detect type -> validate -> security scan -> AI analysis -> persist.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize service with database session.

        Args:
            db: Async SQLAlchemy session for persistence.
        """
        self.db = db
        self.ai_analyzer = AIAnalyzer()

    async def validate(
        self,
        request: ValidationRequest,
        user_id: int,
    ) -> ValidationResponse:
        """
        Execute full validation pipeline.

        Args:
            request: Validation request with content and options.
            user_id: ID of user initiating validation.

        Returns:
            Complete ValidationResponse with all results.
        """
        start_time = time.time()
        validation_type = self._detect_validation_type(request)

        # Create history record
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

        try:
            # Run type-specific validation
            if validation_type in ("yaml", "auto"):
                yaml_result = YamlValidator(request.content, request.file_path).validate_all()
                if yaml_result.is_valid or validation_type == "yaml":
                    findings.extend(yaml_result.findings)
                    metadata.update(yaml_result.metadata)
                    validation_type = "yaml" if yaml_result.file_type != "generic" else validation_type

            if validation_type in ("terraform", "auto") or request.file_path.endswith((".tf", ".hcl")):
                tf_result = TerraformValidator(request.content, request.file_path).validate_all()
                findings.extend(tf_result.findings)
                metadata.update(tf_result.metadata)
                validation_type = "terraform"
                if tf_result.formatted_content:
                    corrected_content = tf_result.formatted_content

            # Security scanning
            if request.include_security_scan:
                scan_result = SecurityScanner(
                    request.content, request.file_path, validation_type
                ).scan_all()
                security_findings = scan_result.findings
                metadata["scanners_run"] = scan_result.scanners_run

            # AI analysis
            if request.include_ai_analysis:
                language = "terraform" if validation_type == "terraform" else "yaml"
                ai_explanations = await self.ai_analyzer.explain_lines(
                    request.content, request.file_path, language
                )
                corrected, findings = await self.ai_analyzer.generate_fixes(
                    request.content, findings, language
                )
                if corrected:
                    corrected_content = corrected

            # Calculate counts
            error_count = sum(
                1 for f in findings if f.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH)
            )
            warning_count = sum(
                1 for f in findings if f.severity in (SeverityLevel.MEDIUM, SeverityLevel.LOW)
            )

            # Determine status
            if error_count > 0:
                status = ValidationStatus.FAILED
            elif warning_count > 0 or security_findings:
                status = ValidationStatus.WARNING
            else:
                status = ValidationStatus.SUCCESS

            duration_ms = int((time.time() - start_time) * 1000)

            # Update history
            history.status = status
            history.validation_type = validation_type
            history.duration_ms = duration_ms
            history.error_count = error_count
            history.warning_count = warning_count
            history.security_findings_count = len(security_findings)
            history.summary = self._generate_summary(error_count, warning_count, len(security_findings))

            # Persist results
            await self._persist_results(history, findings, security_findings, ai_explanations)
            await self.db.commit()

            return ValidationResponse(
                validation_id=history.id,
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
                summary=history.summary,
                metadata=metadata,
            )

        except Exception as e:
            history.status = ValidationStatus.FAILED
            history.summary = f"Validation failed: {str(e)}"
            await self.db.commit()
            raise

    def _detect_validation_type(self, request: ValidationRequest) -> str:
        """Auto-detect validation type from file path and content."""
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
    ) -> None:
        """Persist validation results to database."""
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
                    file_path=history.validation_type,
                    line_number=exp.line_number,
                    code=exp.code,
                    explanation=exp.explanation,
                    risk_level=severity_map.get(exp.risk_level, DBSeverity.INFORMATIONAL),
                    recommendation=exp.recommendation,
                )
            )

    @staticmethod
    def _generate_summary(errors: int, warnings: int, security: int) -> str:
        """Generate human-readable validation summary."""
        parts = []
        if errors:
            parts.append(f"{errors} error(s)")
        if warnings:
            parts.append(f"{warnings} warning(s)")
        if security:
            parts.append(f"{security} security finding(s)")
        return ", ".join(parts) if parts else "All checks passed"
