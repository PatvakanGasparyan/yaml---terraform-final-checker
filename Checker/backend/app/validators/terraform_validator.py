"""
Terraform validation engine.

Provides terraform validate, fmt, plan analysis, provider checks,
variable analysis, module validation, and dependency graph generation.
"""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.schemas import SeverityLevel, ValidationFinding


@dataclass
class TerraformValidationResult:
    """Aggregated Terraform validation output."""

    is_valid: bool
    findings: list[ValidationFinding] = field(default_factory=list)
    providers: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    modules: list[dict[str, Any]] = field(default_factory=list)
    resources: list[dict[str, Any]] = field(default_factory=list)
    dependency_graph: dict[str, Any] = field(default_factory=dict)
    estimated_cost: float | None = None
    formatted_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class TerraformValidator:
    """
    Enterprise Terraform validation engine.

    Uses terraform CLI when available, with fallback static analysis.
    """

    # HCL block patterns for static analysis
    RESOURCE_PATTERN = re.compile(
        r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{', re.MULTILINE
    )
    MODULE_PATTERN = re.compile(r'module\s+"([^"]+)"\s*\{', re.MULTILINE)
    VARIABLE_PATTERN = re.compile(r'variable\s+"([^"]+)"\s*\{', re.MULTILINE)
    PROVIDER_PATTERN = re.compile(r'provider\s+"([^"]+)"\s*\{', re.MULTILINE)
    OUTPUT_PATTERN = re.compile(r'output\s+"([^"]+)"\s*\{', re.MULTILINE)
    DATA_PATTERN = re.compile(r'data\s+"([^"]+)"\s+"([^"]+)"\s*\{', re.MULTILINE)

    # Security-sensitive patterns
    SECRET_PATTERNS = [
        (re.compile(r'password\s*=\s*"[^"]+"', re.IGNORECASE), "Hardcoded password"),
        (re.compile(r'secret\s*=\s*"[^"]+"', re.IGNORECASE), "Hardcoded secret"),
        (re.compile(r'api_key\s*=\s*"[^"]+"', re.IGNORECASE), "Hardcoded API key"),
        (re.compile(r'access_key\s*=\s*"[^"]+"', re.IGNORECASE), "Hardcoded access key"),
    ]

    def __init__(self, content: str, file_path: str = "main.tf") -> None:
        """
        Initialize Terraform validator.

        Args:
            content: HCL/Terraform file content or multi-file project as dict.
            file_path: Primary file path for reporting.
        """
        self.content = content
        self.file_path = file_path
        self.lines = content.splitlines()

    def validate_all(self) -> TerraformValidationResult:
        """
        Run all Terraform validation checks.

        Returns:
            TerraformValidationResult with findings and metadata.
        """
        findings: list[ValidationFinding] = []

        # Static analysis (always available)
        findings.extend(self._analyze_syntax())
        findings.extend(self._analyze_variables())
        findings.extend(self._analyze_providers())
        findings.extend(self._analyze_modules())
        findings.extend(self._analyze_resources())
        findings.extend(self._detect_secrets())
        findings.extend(self._analyze_best_practices())

        providers = self._extract_providers()
        variables = self._extract_variables()
        modules = self._extract_modules()
        resources = self._extract_resources()
        graph = self._build_dependency_graph(resources)

        # Try CLI validation if terraform is installed
        cli_findings = self._run_terraform_validate()
        findings.extend(cli_findings)

        fmt_result = self._run_terraform_fmt_check()
        findings.extend(fmt_result)

        errors = [f for f in findings if f.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH)]

        return TerraformValidationResult(
            is_valid=len(errors) == 0,
            findings=findings,
            providers=providers,
            variables=variables,
            modules=modules,
            resources=resources,
            dependency_graph=graph,
            estimated_cost=self._estimate_cost(resources),
            formatted_content=fmt_result[0].corrected_code if fmt_result else None,
            metadata={
                "resource_count": len(resources),
                "module_count": len(modules),
                "provider_count": len(providers),
                "variable_count": len(variables),
            },
        )

    def _analyze_syntax(self) -> list[ValidationFinding]:
        """Basic HCL syntax validation."""
        findings: list[ValidationFinding] = []
        brace_count = 0

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue

            brace_count += line.count("{") - line.count("}")

            # Unbalanced quotes
            if line.count('"') % 2 != 0 and not stripped.endswith("\\"):
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=i,
                        severity=SeverityLevel.HIGH,
                        category="syntax",
                        message="Unbalanced double quotes",
                        rule_id="TF001",
                        original_code=line,
                    )
                )

        if brace_count != 0:
            findings.append(
                ValidationFinding(
                    file_path=self.file_path,
                    severity=SeverityLevel.CRITICAL,
                    category="syntax",
                    message=f"Unbalanced braces: {'missing closing' if brace_count > 0 else 'extra closing'} brace(s)",
                    rule_id="TF002",
                )
            )

        return findings

    def _analyze_variables(self) -> list[ValidationFinding]:
        """Analyze Terraform variable definitions."""
        findings: list[ValidationFinding] = []

        for match in self.VARIABLE_PATTERN.finditer(self.content):
            var_name = match.group(1)
            var_block = self._extract_block(match.start())

            if "type" not in var_block:
                line = self.content[: match.start()].count("\n") + 1
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=line,
                        severity=SeverityLevel.MEDIUM,
                        category="variables",
                        message=f"Variable '{var_name}' missing type declaration",
                        rule_id="TF_VAR001",
                        recommendation="Add explicit type = string|number|bool|list|map",
                    )
                )

            if "description" not in var_block:
                line = self.content[: match.start()].count("\n") + 1
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=line,
                        severity=SeverityLevel.LOW,
                        category="variables",
                        message=f"Variable '{var_name}' missing description",
                        rule_id="TF_VAR002",
                    )
                )

        return findings

    def _analyze_providers(self) -> list[ValidationFinding]:
        """Analyze provider configurations and compatibility."""
        findings: list[ValidationFinding] = []

        for match in self.PROVIDER_PATTERN.finditer(self.content):
            provider_name = match.group(1)
            line = self.content[: match.start()].count("\n") + 1

            # Check for version constraints in terraform block
            if "version" not in self.content and "required_providers" not in self.content:
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=line,
                        severity=SeverityLevel.MEDIUM,
                        category="providers",
                        message=f"Provider '{provider_name}' has no version constraint",
                        rule_id="TF_PROV001",
                        recommendation="Add required_providers block with version constraints",
                    )
                )

        return findings

    def _analyze_modules(self) -> list[ValidationFinding]:
        """Validate Terraform module references."""
        findings: list[ValidationFinding] = []

        for match in self.MODULE_PATTERN.finditer(self.content):
            module_name = match.group(1)
            module_block = self._extract_block(match.start())
            line = self.content[: match.start()].count("\n") + 1

            if "source" not in module_block:
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=line,
                        severity=SeverityLevel.CRITICAL,
                        category="modules",
                        message=f"Module '{module_name}' missing source attribute",
                        rule_id="TF_MOD001",
                    )
                )

        return findings

    def _analyze_resources(self) -> list[ValidationFinding]:
        """Analyze Terraform resource definitions."""
        findings: list[ValidationFinding] = []

        for match in self.RESOURCE_PATTERN.finditer(self.content):
            resource_type = match.group(1)
            resource_name = match.group(2)
            line = self.content[: match.start()].count("\n") + 1

            # Public S3 bucket check
            if resource_type == "aws_s3_bucket":
                block = self._extract_block(match.start())
                if "acl" in block and '"public-read"' in block:
                    findings.append(
                        ValidationFinding(
                            file_path=self.file_path,
                            line_number=line,
                            severity=SeverityLevel.CRITICAL,
                            category="security",
                            message=f"S3 bucket '{resource_name}' configured with public-read ACL",
                            rule_id="TF_SEC001",
                            impact="Public bucket exposes data to the internet",
                        )
                    )

            # Open security group
            if resource_type == "aws_security_group":
                block = self._extract_block(match.start())
                normalized = re.sub(r"\s+", "", block)
                if 'cidr_blocks=["0.0.0.0/0"]' in normalized:
                    findings.append(
                        ValidationFinding(
                            file_path=self.file_path,
                            line_number=line,
                            severity=SeverityLevel.HIGH,
                            category="security",
                            message=f"Security group '{resource_name}' allows traffic from 0.0.0.0/0",
                            rule_id="TF_SEC002",
                            impact="Open ingress rule exposes resources to the internet",
                        )
                    )

        return findings

    def _detect_secrets(self) -> list[ValidationFinding]:
        """Detect hardcoded secrets in Terraform files."""
        findings: list[ValidationFinding] = []

        for pattern, description in self.SECRET_PATTERNS:
            for match in pattern.finditer(self.content):
                line = self.content[: match.start()].count("\n") + 1
                findings.append(
                    ValidationFinding(
                        file_path=self.file_path,
                        line_number=line,
                        severity=SeverityLevel.CRITICAL,
                        category="secrets",
                        message=description,
                        rule_id="TF_SEC003",
                        original_code=self.lines[line - 1] if line <= len(self.lines) else None,
                        recommendation="Use variables with sensitive = true or secret manager",
                        impact="Hardcoded secrets in version control are a critical security risk",
                    )
                )

        return findings

    def _analyze_best_practices(self) -> list[ValidationFinding]:
        """Terraform best practice analysis."""
        findings: list[ValidationFinding] = []

        if "terraform {" not in self.content:
            findings.append(
                ValidationFinding(
                    file_path=self.file_path,
                    severity=SeverityLevel.MEDIUM,
                    category="best_practice",
                    message="Missing terraform {} configuration block",
                    rule_id="TF_BP001",
                    recommendation="Add terraform block with required_version and backend config",
                )
            )

        if "backend" not in self.content:
            findings.append(
                ValidationFinding(
                    file_path=self.file_path,
                    severity=SeverityLevel.MEDIUM,
                    category="best_practice",
                    message="No remote backend configured",
                    rule_id="TF_BP002",
                    recommendation="Configure S3/GCS/Azure backend for state management",
                )
            )

        return findings

    def _extract_block(self, start_pos: int) -> str:
        """Extract HCL block content from start position."""
        brace_count = 0
        block_start = self.content.find("{", start_pos)
        if block_start == -1:
            return ""

        for i in range(block_start, len(self.content)):
            if self.content[i] == "{":
                brace_count += 1
            elif self.content[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    return self.content[block_start : i + 1]
        return ""

    def _extract_providers(self) -> dict[str, Any]:
        """Extract provider definitions."""
        providers = {}
        for match in self.PROVIDER_PATTERN.finditer(self.content):
            providers[match.group(1)] = {"line": self.content[: match.start()].count("\n") + 1}
        return providers

    def _extract_variables(self) -> dict[str, Any]:
        """Extract variable definitions."""
        variables = {}
        for match in self.VARIABLE_PATTERN.finditer(self.content):
            variables[match.group(1)] = {"line": self.content[: match.start()].count("\n") + 1}
        return variables

    def _extract_modules(self) -> list[dict[str, Any]]:
        """Extract module definitions."""
        modules = []
        for match in self.MODULE_PATTERN.finditer(self.content):
            modules.append({
                "name": match.group(1),
                "line": self.content[: match.start()].count("\n") + 1,
            })
        return modules

    def _extract_resources(self) -> list[dict[str, Any]]:
        """Extract resource definitions."""
        resources = []
        for match in self.RESOURCE_PATTERN.finditer(self.content):
            resources.append({
                "type": match.group(1),
                "name": match.group(2),
                "line": self.content[: match.start()].count("\n") + 1,
            })
        return resources

    def _build_dependency_graph(self, resources: list[dict[str, Any]]) -> dict[str, Any]:
        """Build resource dependency graph from references."""
        nodes = [{"id": f"{r['type']}.{r['name']}", "type": r["type"]} for r in resources]
        edges: list[dict[str, str]] = []

        # Detect depends_on and resource references
        depends_pattern = re.compile(r'depends_on\s*=\s*\[(.*?)\]', re.DOTALL)
        ref_pattern = re.compile(r'(\w+\.\w+\.\w+)')

        for match in self.RESOURCE_PATTERN.finditer(self.content):
            source = f"{match.group(1)}.{match.group(2)}"
            block = self._extract_block(match.start())

            for dep_match in depends_pattern.finditer(block):
                deps = re.findall(r'(\w+\.\w+)', dep_match.group(1))
                for dep in deps:
                    edges.append({"from": source, "to": dep, "type": "depends_on"})

            for ref_match in ref_pattern.finditer(block):
                target = ref_match.group(1)
                if target != source and "." in target:
                    parts = target.split(".")
                    if len(parts) >= 2:
                        ref_id = f"{parts[0]}.{parts[1]}"
                        if ref_id != source:
                            edges.append({"from": source, "to": ref_id, "type": "reference"})

        return {"nodes": nodes, "edges": edges}

    def _estimate_cost(self, resources: list[dict[str, Any]]) -> float | None:
        """Basic cost estimation based on resource types."""
        cost_map = {
            "aws_instance": 50.0,
            "aws_rds_instance": 100.0,
            "aws_s3_bucket": 5.0,
            "aws_lambda_function": 10.0,
            "azurerm_virtual_machine": 60.0,
            "google_compute_instance": 55.0,
        }
        total = sum(cost_map.get(r["type"], 0) for r in resources)
        return total if total > 0 else None

    def _run_terraform_validate(self) -> list[ValidationFinding]:
        """Run terraform validate CLI if available."""
        findings: list[ValidationFinding] = []

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tf_file = Path(tmpdir) / "main.tf"
                tf_file.write_text(self.content)

                result = subprocess.run(
                    ["terraform", "init", "-backend=false", "-no-color"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )

                if result.returncode != 0:
                    findings.append(
                        ValidationFinding(
                            file_path=self.file_path,
                            severity=SeverityLevel.HIGH,
                            category="terraform_cli",
                            message=f"terraform init failed: {result.stderr[:500]}",
                            rule_id="TF_CLI001",
                        )
                    )
                    return findings

                result = subprocess.run(
                    ["terraform", "validate", "-no-color", "-json"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=tmpdir,
                )

                if result.stdout:
                    try:
                        output = json.loads(result.stdout)
                        if not output.get("valid", True):
                            for diag in output.get("diagnostics", []):
                                findings.append(
                                    ValidationFinding(
                                        file_path=self.file_path,
                                        line_number=diag.get("range", {}).get("start", {}).get("line"),
                                        severity=SeverityLevel.HIGH,
                                        category="terraform_cli",
                                        message=diag.get("summary", "Validation error"),
                                        rule_id="TF_CLI002",
                                    )
                                )
                    except json.JSONDecodeError:
                        pass

        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # Terraform CLI not available - static analysis only

        return findings

    def _run_terraform_fmt_check(self) -> list[ValidationFinding]:
        """Check terraform formatting."""
        findings: list[ValidationFinding] = []

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tf_file = Path(tmpdir) / "main.tf"
                tf_file.write_text(self.content)

                result = subprocess.run(
                    ["terraform", "fmt", "-check", "-diff", "-no-color"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=tmpdir,
                )

                if result.returncode != 0:
                    # Apply terraform fmt so we can read the corrected file
                    subprocess.run(
                        ["terraform", "fmt", "-no-color"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=tmpdir,
                    )
                    formatted = tf_file.read_text() if tf_file.exists() else None

                    findings.append(
                        ValidationFinding(
                            file_path=self.file_path,
                            severity=SeverityLevel.LOW,
                            category="formatting",
                            message="Terraform formatting does not match terraform fmt standard",
                            rule_id="TF_FMT001",
                            original_code=self.content,
                            corrected_code=formatted,
                            correction_reason="Run terraform fmt to standardize formatting",
                        )
                    )

        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return findings
