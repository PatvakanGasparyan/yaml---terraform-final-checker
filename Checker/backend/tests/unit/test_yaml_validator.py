"""
Unit tests for YAML validation engine.
"""

import pytest

from app.validators.yaml_validator import YamlValidator


class TestYamlValidator:
    """Test YAML validation functionality."""

    def test_valid_yaml(self) -> None:
        """Valid YAML should pass syntax check."""
        content = "name: test\nversion: 1.0"
        result = YamlValidator(content, "test.yaml").validate_all()
        assert result.is_valid
        assert result.parsed_content == {"name": "test", "version": 1.0}

    def test_invalid_yaml_syntax(self) -> None:
        """Invalid YAML syntax should produce critical finding."""
        content = "name: test\n  bad indent: value"
        result = YamlValidator(content, "test.yaml").validate_all()
        assert not result.is_valid
        assert any(f.category == "syntax" for f in result.findings)

    def test_duplicate_keys(self) -> None:
        """Duplicate keys should be detected."""
        content = "key: value1\nkey: value2"
        result = YamlValidator(content, "test.yaml").validate_all()
        assert any(f.category == "duplicate_key" for f in result.findings)

    def test_kubernetes_detection(self) -> None:
        """Kubernetes manifests should be auto-detected."""
        content = """apiVersion: v1
kind: Pod
metadata:
  name: test
spec:
  containers:
  - name: nginx
    image: nginx
"""
        validator = YamlValidator(content, "pod.yaml")
        result = validator.validate_all()
        assert result.file_type == "kubernetes"

    def test_kubernetes_privileged_container(self) -> None:
        """Privileged containers should trigger critical finding."""
        content = """apiVersion: v1
kind: Pod
metadata:
  name: test
spec:
  containers:
  - name: nginx
    image: nginx
    securityContext:
      privileged: true
"""
        result = YamlValidator(content, "pod.yaml").validate_all()
        assert any(f.rule_id == "K8S_SEC001" for f in result.findings)

    def test_tab_detection(self) -> None:
        """Tab characters should trigger best practice warning."""
        content = "name:\tvalue"
        result = YamlValidator(content, "test.yaml").validate_all()
        assert any(f.rule_id == "YAML_BP001" for f in result.findings)

    def test_trailing_whitespace(self) -> None:
        """Trailing whitespace should be detected."""
        content = "name: value  "
        result = YamlValidator(content, "test.yaml").validate_all()
        assert any(f.rule_id == "YAML_BP002" for f in result.findings)
