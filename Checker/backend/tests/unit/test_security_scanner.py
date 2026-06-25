"""
Unit tests for security scanner.
"""

import pytest

from app.security.scanner import SecurityScanner
from app.schemas import SeverityLevel


class TestSecurityScanner:
    """Test security scanning functionality."""

    def test_aws_access_key_detection(self) -> None:
        """AWS access keys should be detected."""
        content = 'aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"'
        result = SecurityScanner(content, "config.tf", "terraform").scan_all()
        assert any(f.severity == SeverityLevel.CRITICAL for f in result.findings)

    def test_github_token_detection(self) -> None:
        """GitHub tokens should be detected."""
        content = "token: ghp_123456789012345678901234567890123456"
        result = SecurityScanner(content, "config.yaml", "yaml").scan_all()
        assert any("GitHub" in f.title for f in result.findings)

    def test_open_ingress_detection(self) -> None:
        """Open ingress rules should be flagged."""
        content = "cidr: 0.0.0.0/0"
        result = SecurityScanner(content, "sg.tf", "terraform").scan_all()
        assert any("0.0.0.0/0" in f.title for f in result.findings)

    def test_privileged_container(self) -> None:
        """Privileged containers should be detected."""
        content = "privileged: true"
        result = SecurityScanner(content, "pod.yaml", "yaml").scan_all()
        assert any("Privileged" in f.title for f in result.findings)

    def test_private_key_detection(self) -> None:
        """Private keys should be detected."""
        content = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        result = SecurityScanner(content, "key.pem", "yaml").scan_all()
        assert any("Private Key" in f.title for f in result.findings)

    def test_scanners_run_list(self) -> None:
        """Static scanners should always run."""
        content = "name: test"
        result = SecurityScanner(content, "test.yaml").scan_all()
        assert "static_patterns" in result.scanners_run
        assert "static_iac" in result.scanners_run
