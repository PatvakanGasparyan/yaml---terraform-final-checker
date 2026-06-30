"""
YAML validation engine.

Provides syntax validation, schema validation, Kubernetes/Helm/Docker Compose/
GitHub Actions/GitLab CI validation, duplicate key detection, and best practices.
"""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

import yaml
from jsonschema import Draft7Validator

from app.schemas import SeverityLevel, ValidationFinding


@dataclass
class YamlValidationResult:
    """Aggregated YAML validation output."""

    is_valid: bool
    findings: list[ValidationFinding] = field(default_factory=list)
    parsed_content: Any = None
    file_type: str = "generic"
    metadata: dict[str, Any] = field(default_factory=dict)


class YamlValidator:
    """
    Enterprise YAML validation engine.

    Supports multiple YAML dialects and best-practice analysis.
    """

    # Kubernetes API version patterns
    K8S_API_VERSIONS = re.compile(r"^v\d+(\.\d+)?$|^apps/v\d+$|^batch/v\d+$|^networking\.k8s\.io/v\d+$")
    # GitHub Actions workflow indicators
    GHA_INDICATORS = {"on:", "jobs:", "runs-on:"}
    # GitLab CI indicators
    GITLAB_CI_INDICATORS = {"stages:", "variables:", "before_script:"}
    # Docker Compose indicators
    COMPOSE_INDICATORS = {"services:", "version:", "networks:", "volumes:"}

    def __init__(self, content: str, file_path: str = "unknown.yaml") -> None:
        """
        Initialize validator with YAML content and virtual file path.

        Args:
            content: Raw YAML string to validate.
            file_path: Path used for finding location reporting.
        """
        self.content = content
        self.file_path = file_path
        self.lines = content.splitlines()

    def validate_all(self) -> YamlValidationResult:
        """
        Run all YAML validation checks.

        Returns:
            YamlValidationResult with all findings aggregated.
        """
        findings: list[ValidationFinding] = []
        parsed: Any = None
        file_type = self._detect_file_type()

        # Step 1: Syntax validation
        syntax_result = self._validate_syntax()
        findings.extend(syntax_result.findings)
        parsed = syntax_result.parsed_content

        if not syntax_result.is_valid:
            return YamlValidationResult(
                is_valid=False,
                findings=findings,
                file_type=file_type,
                metadata={"checks_run": ["syntax"]},
            )

        # Step 2: Duplicate key detection
        findings.extend(self._detect_duplicate_keys())

        # Step 3: Type-specific validation
        if file_type == "kubernetes":
            findings.extend(self._validate_kubernetes(parsed))
        elif file_type == "helm":
            findings.extend(self._validate_helm(parsed))
        elif file_type == "docker_compose":
            findings.extend(self._validate_docker_compose(parsed))
        elif file_type == "github_actions":
            findings.extend(self._validate_github_actions(parsed))
        elif file_type == "gitlab_ci":
            findings.extend(self._validate_gitlab_ci(parsed))

        # Step 4: Best practices
        findings.extend(self._analyze_best_practices())

        # Step 5: Formatting analysis
        findings.extend(self._analyze_formatting())

        errors = [f for f in findings if f.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH)]
        return YamlValidationResult(
            is_valid=len(errors) == 0,
            findings=findings,
            parsed_content=parsed,
            file_type=file_type,
            metadata={
                "checks_run": ["syntax", "duplicates", file_type, "best_practices", "formatting"],
                "line_count": len(self.lines),
                "content_hash": hashlib.sha256(self.content.encode()).hexdigest(),
            },
        )

    def _validate_syntax(self) -> YamlValidationResult:
        """Validate YAML syntax using PyYAML loader."""
        findings: list[ValidationFinding] = []
        parsed: Any = None

        try:
            parsed = yaml.safe_load(self.content)
            if parsed is None and self.content.strip():
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=1,
                        severity=SeverityLevel.MEDIUM,
                        category="syntax",
                        message="YAML parsed to null/empty document",
                    )
                )
        except yaml.YAMLError as e:
            line_num = getattr(e, "problem_mark", None)
            line = line_num.line + 1 if line_num else None
            col = line_num.column + 1 if line_num else None
            findings.append(
                ValidationFinding(
                    file_path=self.file_path,
                    line_number=line,
                    column_number=col,
                    severity=SeverityLevel.CRITICAL,
                    category="syntax",
                    message=f"YAML syntax error: {e}",
                    original_code=self.lines[line - 1] if line and line <= len(self.lines) else None,
                )
            )
            return YamlValidationResult(is_valid=False, findings=findings)

        return YamlValidationResult(is_valid=True, findings=findings, parsed_content=parsed)

    def _detect_duplicate_keys(self) -> list[ValidationFinding]:
        """Detect duplicate keys at the same mapping level."""
        findings: list[ValidationFinding] = []

        class DuplicateKeyLoader(yaml.SafeLoader):
            pass

        def mapping_constructor(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict:
            mapping: dict = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node)
                if key in mapping:
                    line = key_node.start_mark.line + 1 if key_node.start_mark else None
                    findings.append(
                        ValidationFinding(
                            file_path=self.file_path,
                            line_number=line,
                            severity=SeverityLevel.HIGH,
                            category="duplicate_key",
                            message=f"Duplicate key found: '{key}'",
                            original_code=self.lines[line - 1] if line and line <= len(self.lines) else None,
                        )
                    )
                mapping[key] = loader.construct_object(value_node)
            return mapping

        DuplicateKeyLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping_constructor
        )

        try:
            yaml.load(self.content, Loader=DuplicateKeyLoader)
        except yaml.YAMLError:
            pass  # Syntax errors already caught

        return findings

    def _detect_file_type(self) -> str:
        """Auto-detect YAML file type from path and content."""
        path_lower = self.file_path.lower()
        content_lower = self.content.lower()

        if "chart.yaml" in path_lower or "values.yaml" in path_lower:
            return "helm"
        if "docker-compose" in path_lower or "compose.yaml" in path_lower:
            return "docker_compose"
        if ".github/workflows" in path_lower:
            return "github_actions"
        if ".gitlab-ci" in path_lower:
            return "gitlab_ci"
        if any(k in content_lower for k in ("apiversion:", "kind:", "metadata:")):
            return "kubernetes"
        if self.GHA_INDICATORS.issubset(set(content_lower.split())):
            return "github_actions"
        if self.GITLAB_CI_INDICATORS.intersection(set(content_lower.split())):
            return "gitlab_ci"
        tokens = set(content_lower.split())
        if "services:" in tokens:
            return "docker_compose"

        return "generic"

    def _validate_kubernetes(self, parsed: Any) -> list[ValidationFinding]:
        """Validate Kubernetes manifest structure."""
        findings: list[ValidationFinding] = []

        manifests = parsed if isinstance(parsed, list) else [parsed]
        for i, manifest in enumerate(manifests):
            if not isinstance(manifest, dict):
                continue

            # Required fields
            for required_field in ("apiVersion", "kind", "metadata"):
                if required_field not in manifest:
                    findings.append(
                        ValidationFinding(
                            file_path=self.file_path,
                            severity=SeverityLevel.HIGH,
                            category="kubernetes",
                            message=f"Missing required field '{required_field}' in manifest #{i + 1}",
                            rule_id="K8S001",
                        )
                    )

            # apiVersion format
            api_version = manifest.get("apiVersion", "")
            if api_version and not self.K8S_API_VERSIONS.match(str(api_version)):
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        severity=SeverityLevel.MEDIUM,
                        category="kubernetes",
                        message=f"Unusual apiVersion format: '{api_version}'",
                        rule_id="K8S002",
                    )
                )

            # Security: privileged containers
            spec = manifest.get("spec", {})
            containers = spec.get("containers", []) if isinstance(spec, dict) else []
            template = spec.get("template", {}).get("spec", {}) if isinstance(spec, dict) else {}
            containers.extend(template.get("containers", []) if isinstance(template, dict) else [])

            for container in containers:
                if isinstance(container, dict):
                    security_ctx = container.get("securityContext", {})
                    if security_ctx.get("privileged"):
                        findings.append(
                            ValidationFinding(
                                file_path=self.file_path,
                                severity=SeverityLevel.CRITICAL,
                                category="kubernetes_security",
                                message=f"Container '{container.get('name', 'unknown')}' runs as privileged",
                                rule_id="K8S_SEC001",
                                impact="Privileged containers have full host access",
                            )
                        )

        return findings

    def _validate_helm(self, parsed: Any) -> list[ValidationFinding]:
        """Validate Helm chart.yaml or values.yaml."""
        findings: list[ValidationFinding] = []

        if not isinstance(parsed, dict):
            return findings

        if "chart.yaml" in self.file_path.lower():
            for field_name in ("apiVersion", "name", "version"):
                if field_name not in parsed:
                    findings.append(
                        ValidationFinding(
                            file_path=self.file_path,
                            severity=SeverityLevel.HIGH,
                            category="helm",
                            message=f"Missing required Chart.yaml field: '{field_name}'",
                            rule_id="HELM001",
                        )
                    )

        return findings

    def _validate_docker_compose(self, parsed: Any) -> list[ValidationFinding]:
        """Validate Docker Compose file structure."""
        findings: list[ValidationFinding] = []

        if not isinstance(parsed, dict):
            return findings

        if "services" not in parsed:
            findings.append(
                ValidationFinding(
                    file_path=self.file_path,
                    severity=SeverityLevel.HIGH,
                    category="docker_compose",
                    message="Missing required 'services' section",
                    rule_id="COMPOSE001",
                )
            )
            return findings

        services = parsed.get("services", {})
        for service_name, service_config in services.items():
            if isinstance(service_config, dict):
                # Check for exposed ports without restrictions
                ports = service_config.get("ports", [])
                if ports and not service_config.get("networks"):
                    findings.append(
                        ValidationFinding(
                            file_path=self.file_path,
                            severity=SeverityLevel.LOW,
                            category="docker_compose",
                            message=f"Service '{service_name}' exposes ports without explicit network config",
                            rule_id="COMPOSE002",
                        )
                    )

        return findings

    def _validate_github_actions(self, parsed: Any) -> list[ValidationFinding]:
        """Validate GitHub Actions workflow file."""
        findings: list[ValidationFinding] = []

        if not isinstance(parsed, dict):
            return findings

        if "on" not in parsed and True not in parsed:
            findings.append(
                ValidationFinding(
                    file_path=self.file_path,
                    severity=SeverityLevel.HIGH,
                    category="github_actions",
                    message="Missing 'on' trigger definition",
                    rule_id="GHA001",
                )
            )

        jobs = parsed.get("jobs", {})
        for job_name, job_config in jobs.items():
            if isinstance(job_config, dict) and "runs-on" not in job_config:
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        severity=SeverityLevel.HIGH,
                        category="github_actions",
                        message=f"Job '{job_name}' missing 'runs-on' field",
                        rule_id="GHA002",
                    )
                )

        return findings

    def _validate_gitlab_ci(self, parsed: Any) -> list[ValidationFinding]:
        """Validate GitLab CI configuration."""
        findings: list[ValidationFinding] = []

        if not isinstance(parsed, dict):
            return findings

        # Check for script in jobs without stages
        has_stages = "stages" in parsed
        job_keys = {k for k in parsed if k not in ("stages", "variables", "before_script", "after_script", "include")}

        for job_name in job_keys:
            job = parsed.get(job_name, {})
            if isinstance(job, dict) and "script" not in job and "extends" not in job:
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        severity=SeverityLevel.MEDIUM,
                        category="gitlab_ci",
                        message=f"Job '{job_name}' has no 'script' or 'extends' defined",
                        rule_id="GLCI001",
                    )
                )

        if not has_stages and job_keys:
            findings.append(
                ValidationFinding(
                    file_path=self.file_path,
                    severity=SeverityLevel.INFORMATIONAL,
                    category="gitlab_ci",
                    message="No explicit 'stages' defined; using default stage order",
                    rule_id="GLCI002",
                )
            )

        return findings

    def _analyze_best_practices(self) -> list[ValidationFinding]:
        """Analyze YAML best practices."""
        findings: list[ValidationFinding] = []

        for i, line in enumerate(self.lines, 1):
            # Tab characters in YAML
            if "\t" in line:
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=i,
                        severity=SeverityLevel.MEDIUM,
                        category="best_practice",
                        message="Tab character found; use spaces for indentation",
                        rule_id="YAML_BP001",
                        original_code=line,
                        corrected_code=line.replace("\t", "  "),
                        correction_reason="YAML spec requires space indentation",
                    )
                )

            # Trailing whitespace
            if line != line.rstrip():
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=i,
                        severity=SeverityLevel.LOW,
                        category="best_practice",
                        message="Trailing whitespace detected",
                        rule_id="YAML_BP002",
                        original_code=line,
                        corrected_code=line.rstrip(),
                    )
                )

        return findings

    def _analyze_formatting(self) -> list[ValidationFinding]:
        """Analyze YAML formatting consistency."""
        findings: list[ValidationFinding] = []
        indent_sizes: set[int] = set()

        for line in self.lines:
            if line.strip() and not line.strip().startswith("#"):
                indent = len(line) - len(line.lstrip())
                if indent > 0:
                    indent_sizes.add(indent)

        # Check for inconsistent indentation
        if len(indent_sizes) > 1:
            gcd = self._find_common_indent(list(indent_sizes))
            if gcd and any(size % gcd != 0 for size in indent_sizes if size > 0):
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        severity=SeverityLevel.LOW,
                        category="formatting",
                        message="Inconsistent indentation detected",
                        rule_id="YAML_FMT001",
                    )
                )

        return findings

    @staticmethod
    def _find_common_indent(sizes: list[int]) -> int:
        """Find GCD of indent sizes."""
        from math import gcd
        from functools import reduce

        non_zero = [s for s in sizes if s > 0]
        if not non_zero:
            return 2
        return reduce(gcd, non_zero)

    @staticmethod
    def validate_schema(content: str, schema: dict[str, Any], file_path: str = "unknown.yaml") -> list[ValidationFinding]:
        """
        Validate YAML content against a JSON Schema.

        Args:
            content: YAML string.
            schema: JSON Schema dict.
            file_path: File path for reporting.

        Returns:
            List of schema validation findings.
        """
        findings: list[ValidationFinding] = []
        try:
            parsed = yaml.safe_load(content)
            validator = Draft7Validator(schema)
            for error in validator.iter_errors(parsed):
                findings.append(
                    ValidationFinding(
                        file_path=file_path,
                        severity=SeverityLevel.HIGH,
                        category="schema",
                        message=error.message,
                        rule_id="SCHEMA001",
                    )
                )
        except yaml.YAMLError as e:
            findings.append(
                ValidationFinding(
                    file_path=file_path,
                    severity=SeverityLevel.CRITICAL,
                    category="syntax",
                    message=str(e),
                )
            )
        return findings
