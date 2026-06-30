"""
Security scanning engine.

Integrates Checkov, tfsec, Trivy, and Semgrep for comprehensive
security analysis of YAML and Terraform configurations.
"""

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.schemas import SecurityFinding, SeverityLevel


@dataclass
class SecurityScanResult:
    """Aggregated security scan output."""

    findings: list[SecurityFinding] = field(default_factory=list)
    scanners_run: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SecurityScanner:
    """
    Multi-scanner security analysis engine.

    Runs Checkov, tfsec, Trivy, and Semgrep with fallback
    static pattern analysis when CLI tools are unavailable.
    """

    # Static secret detection patterns
    SECRET_PATTERNS = [
        (re.compile(r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}'), "API Key"),
        (re.compile(r'(?i)(secret[_-]?key|secretkey)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}'), "Secret Key"),
        (re.compile(r'(?i)(password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']'), "Password"),
        (re.compile(r'(?i)(token|auth[_-]?token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]{20,}'), "Token"),
        (re.compile(r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*["\']?AKIA[0-9A-Z]{16}'), "AWS Access Key"),
        (re.compile(r'(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*["\']?[a-zA-Z0-9/+=]{40}'), "AWS Secret Key"),
        (re.compile(r'ghp_[a-zA-Z0-9]{36}'), "GitHub Personal Access Token"),
        (re.compile(r'gho_[a-zA-Z0-9]{36}'), "GitHub OAuth Token"),
        (re.compile(r'glpat-[a-zA-Z0-9\-_]{20,}'), "GitLab Personal Access Token"),
        (re.compile(r'sk-[a-zA-Z0-9]{20,}'), "OpenAI API Key"),
        (re.compile(r'-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'), "Private Key"),
    ]

    SEVERITY_MAP = {
        "CRITICAL": SeverityLevel.CRITICAL,
        "HIGH": SeverityLevel.HIGH,
        "MEDIUM": SeverityLevel.MEDIUM,
        "LOW": SeverityLevel.LOW,
        "INFO": SeverityLevel.INFORMATIONAL,
        "INFORMATIONAL": SeverityLevel.INFORMATIONAL,
    }

    def __init__(self, content: str, file_path: str, file_type: str = "auto") -> None:
        """
        Initialize security scanner.

        Args:
            content: File content to scan.
            file_path: Virtual file path.
            file_type: yaml, terraform, or auto.
        """
        self.content = content
        self.file_path = file_path
        self.file_type = file_type if file_type != "auto" else self._detect_type()
        self.lines = content.splitlines()

    def scan_all(self) -> SecurityScanResult:
        """
        Run all available security scanners.

        Returns:
            SecurityScanResult with all findings.
        """
        findings: list[SecurityFinding] = []
        scanners_run: list[str] = []

        # Always run static secret detection
        findings.extend(self._static_secret_scan())
        scanners_run.append("static_patterns")

        # Run infrastructure misconfiguration checks
        findings.extend(self._static_misconfiguration_scan())
        scanners_run.append("static_iac")

        # Try CLI scanners
        for scanner_name, scanner_func in [
            ("checkov", self._run_checkov),
            ("tfsec", self._run_tfsec),
            ("trivy", self._run_trivy),
            ("semgrep", self._run_semgrep),
        ]:
            try:
                scanner_findings = scanner_func()
                if scanner_findings is not None:
                    findings.extend(scanner_findings)
                    scanners_run.append(scanner_name)
            except Exception:
                pass  # Scanner not available

        return SecurityScanResult(
            findings=findings,
            scanners_run=scanners_run,
            metadata={
                "total_findings": len(findings),
                "critical_count": sum(1 for f in findings if f.severity == SeverityLevel.CRITICAL),
                "high_count": sum(1 for f in findings if f.severity == SeverityLevel.HIGH),
            },
        )

    def _detect_type(self) -> str:
        """Detect file type from path and content."""
        if self.file_path.endswith((".tf", ".tfvars", ".hcl")):
            return "terraform"
        if self.file_path.endswith((".yaml", ".yml")):
            return "yaml"
        if "resource " in self.content and "provider " in self.content:
            return "terraform"
        return "yaml"

    def _static_secret_scan(self) -> list[SecurityFinding]:
        """Detect secrets using regex patterns."""
        findings: list[SecurityFinding] = []

        for pattern, secret_type in self.SECRET_PATTERNS:
            for match in pattern.finditer(self.content):
                line = self.content[: match.start()].count("\n") + 1
                findings.append(
                    SecurityFinding(
                        scanner="static_patterns",
                        rule_id="SEC001",
                        severity=SeverityLevel.CRITICAL,
                        title=f"Potential {secret_type} detected",
                        description=f"Hardcoded {secret_type.lower()} found in configuration",
                        file_path=self.file_path,
                        line_number=line,
                        remediation="Remove secret from code and use environment variables or secret manager",
                    )
                )

        return findings

    def _static_misconfiguration_scan(self) -> list[SecurityFinding]:
        """Detect common IaC misconfigurations."""
        findings: list[SecurityFinding] = []

        misconfig_checks = [
            (r'0\.0\.0\.0/0', SeverityLevel.HIGH, "Open ingress rule (0.0.0.0/0)", "Restrict CIDR to specific IP ranges"),
            (r'public-read', SeverityLevel.CRITICAL, "Public read access configured", "Use private ACL with bucket policies"),
            (r'privileged:\s*true', SeverityLevel.CRITICAL, "Privileged container", "Remove privileged flag or use securityContext"),
            (r'runAsUser:\s*0', SeverityLevel.HIGH, "Container runs as root (UID 0)", "Set runAsNonRoot: true"),
            (r'allowPrivilegeEscalation:\s*true', SeverityLevel.HIGH, "Privilege escalation allowed", "Set allowPrivilegeEscalation: false"),
            (r'encryption.*false|encrypted\s*=\s*false', SeverityLevel.HIGH, "Encryption disabled", "Enable encryption at rest"),
            (r'http://', SeverityLevel.MEDIUM, "Insecure HTTP endpoint", "Use HTTPS for all endpoints"),
        ]

        for pattern, severity, title, remediation in misconfig_checks:
            for match in re.finditer(pattern, self.content, re.IGNORECASE):
                line = self.content[: match.start()].count("\n") + 1
                findings.append(
                    SecurityFinding(
                        scanner="static_iac",
                        rule_id=f"IAC_{pattern[:10]}",
                        severity=severity,
                        title=title,
                        file_path=self.file_path,
                        line_number=line,
                        remediation=remediation,
                    )
                )

        return findings

    def _run_cli_scanner(
        self,
        command: list[str],
        scanner_name: str,
        parse_func: Any,
        file_ext: str,
    ) -> list[SecurityFinding] | None:
        """Generic CLI scanner runner."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                file_path = Path(tmpdir) / f"scan{file_ext}"
                file_path.write_text(self.content)

                result = subprocess.run(
                    command + [str(tmpdir)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                if result.stdout:
                    return parse_func(result.stdout, scanner_name)
                if result.stderr and scanner_name == "semgrep":
                    return parse_func(result.stderr, scanner_name)

        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        return []

    def _run_checkov(self) -> list[SecurityFinding] | None:
        """Run Checkov IaC scanner."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                ext = ".tf" if self.file_type == "terraform" else ".yaml"
                file_path = Path(tmpdir) / f"scan{ext}"
                file_path.write_text(self.content)
                result = subprocess.run(
                    ["checkov", "-d", tmpdir, "--output", "json", "--quiet"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.stdout:
                    return self._parse_checkov_output(result.stdout, "checkov")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        return []

    def _run_tfsec(self) -> list[SecurityFinding] | None:
        """Run tfsec Terraform scanner."""
        if self.file_type != "terraform":
            return []
        return self._run_cli_scanner(
            ["tfsec", "--format", "json", "--no-color"],
            "tfsec",
            self._parse_tfsec_output,
            ".tf",
        )

    def _run_trivy(self) -> list[SecurityFinding] | None:
        """Run Trivy config scanner."""
        return self._run_cli_scanner(
            ["trivy", "config", "--format", "json", "--quiet"],
            "trivy",
            self._parse_trivy_output,
            ".tf" if self.file_type == "terraform" else ".yaml",
        )

    def _run_semgrep(self) -> list[SecurityFinding] | None:
        """Run Semgrep static analysis."""
        return self._run_cli_scanner(
            ["semgrep", "--config=auto", "--json", "--quiet"],
            "semgrep",
            self._parse_semgrep_output,
            ".tf" if self.file_type == "terraform" else ".yaml",
        )

    def _parse_checkov_output(self, output: str, scanner: str) -> list[SecurityFinding]:
        """Parse Checkov JSON output."""
        findings: list[SecurityFinding] = []
        try:
            data = json.loads(output)
            for result in data if isinstance(data, list) else [data]:
                for check in result.get("results", {}).get("failed_checks", []):
                    findings.append(
                        SecurityFinding(
                            scanner=scanner,
                            rule_id=check.get("check_id", "UNKNOWN"),
                            severity=self.SEVERITY_MAP.get(
                                check.get("severity", "MEDIUM").upper(), SeverityLevel.MEDIUM
                            ),
                            title=check.get("check_name", "Checkov finding"),
                            description=check.get("check_result", {}).get("result", ""),
                            file_path=check.get("file_path", self.file_path),
                            line_number=check.get("file_line_range", [None])[0],
                            resource=check.get("resource"),
                            remediation=check.get("guideline"),
                        )
                    )
        except json.JSONDecodeError:
            pass
        return findings

    def _parse_tfsec_output(self, output: str, scanner: str) -> list[SecurityFinding]:
        """Parse tfsec JSON output."""
        findings: list[SecurityFinding] = []
        try:
            data = json.loads(output)
            for result in data.get("results", []):
                findings.append(
                    SecurityFinding(
                        scanner=scanner,
                        rule_id=result.get("rule_id", "UNKNOWN"),
                        severity=self.SEVERITY_MAP.get(
                            result.get("severity", "MEDIUM").upper(), SeverityLevel.MEDIUM
                        ),
                        title=result.get("rule_description", "tfsec finding"),
                        description=result.get("impact", ""),
                        file_path=result.get("location", {}).get("filename", self.file_path),
                        line_number=result.get("location", {}).get("start_line"),
                        resource=result.get("resource"),
                        remediation=result.get("resolution", ""),
                    )
                )
        except json.JSONDecodeError:
            pass
        return findings

    def _parse_trivy_output(self, output: str, scanner: str) -> list[SecurityFinding]:
        """Parse Trivy JSON output."""
        findings: list[SecurityFinding] = []
        try:
            data = json.loads(output)
            for result in data.get("Results", []):
                for misconfig in result.get("Misconfigurations", []):
                    findings.append(
                        SecurityFinding(
                            scanner=scanner,
                            rule_id=misconfig.get("ID", "UNKNOWN"),
                            severity=self.SEVERITY_MAP.get(
                                misconfig.get("Severity", "MEDIUM").upper(), SeverityLevel.MEDIUM
                            ),
                            title=misconfig.get("Title", "Trivy finding"),
                            description=misconfig.get("Description", ""),
                            file_path=misconfig.get("CauseMetadata", {}).get("File", self.file_path),
                            line_number=misconfig.get("CauseMetadata", {}).get("StartLine"),
                            remediation=misconfig.get("Resolution", ""),
                        )
                    )
        except json.JSONDecodeError:
            pass
        return findings

    def _parse_semgrep_output(self, output: str, scanner: str) -> list[SecurityFinding]:
        """Parse Semgrep JSON output."""
        findings: list[SecurityFinding] = []
        try:
            data = json.loads(output)
            for result in data.get("results", []):
                extra = result.get("extra", {})
                findings.append(
                    SecurityFinding(
                        scanner=scanner,
                        rule_id=result.get("check_id", "UNKNOWN"),
                        severity=self.SEVERITY_MAP.get(
                            extra.get("severity", "MEDIUM").upper(), SeverityLevel.MEDIUM
                        ),
                        title=extra.get("message", "Semgrep finding"),
                        file_path=result.get("path", self.file_path),
                        line_number=result.get("start", {}).get("line"),
                        remediation=extra.get("fix", ""),
                    )
                )
        except json.JSONDecodeError:
            pass
        return findings
