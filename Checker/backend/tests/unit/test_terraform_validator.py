"""
Unit tests for Terraform validation engine.
"""

import pytest

from app.validators.terraform_validator import TerraformValidator


class TestTerraformValidator:
    """Test Terraform validation functionality."""

    def test_valid_terraform(self) -> None:
        """Valid Terraform should pass basic checks."""
        content = '''
resource "aws_s3_bucket" "example" {
  bucket = "my-bucket"
}
'''
        result = TerraformValidator(content, "main.tf").validate_all()
        assert len(result.resources) == 1
        assert result.resources[0]["type"] == "aws_s3_bucket"

    def test_unbalanced_braces(self) -> None:
        """Unbalanced braces should produce critical finding."""
        content = 'resource "aws_s3_bucket" "example" {'
        result = TerraformValidator(content, "main.tf").validate_all()
        assert any(f.rule_id == "TF002" for f in result.findings)

    def test_hardcoded_secret(self) -> None:
        """Hardcoded secrets should be detected."""
        content = 'password = "mysecretpassword123"'
        result = TerraformValidator(content, "main.tf").validate_all()
        assert any(f.category == "secrets" for f in result.findings)

    def test_missing_module_source(self) -> None:
        """Module without source should fail."""
        content = 'module "vpc" {}'
        result = TerraformValidator(content, "main.tf").validate_all()
        assert any(f.rule_id == "TF_MOD001" for f in result.findings)

    def test_public_s3_bucket(self) -> None:
        """Public S3 bucket ACL should trigger critical finding."""
        content = '''
resource "aws_s3_bucket" "public" {
  acl = "public-read"
}
'''
        result = TerraformValidator(content, "main.tf").validate_all()
        assert any(f.rule_id == "TF_SEC001" for f in result.findings)

    def test_open_security_group(self) -> None:
        """Open security group should be flagged."""
        content = '''
resource "aws_security_group" "open" {
  ingress {
    cidr_blocks = ["0.0.0.0/0"]
  }
}
'''
        result = TerraformValidator(content, "main.tf").validate_all()
        assert any(f.rule_id == "TF_SEC002" for f in result.findings)

    def test_dependency_graph(self) -> None:
        """Dependency graph should be generated."""
        content = '''
resource "aws_vpc" "main" {}
resource "aws_subnet" "public" {
  vpc_id = aws_vpc.main.id
}
'''
        result = TerraformValidator(content, "main.tf").validate_all()
        assert len(result.dependency_graph.get("nodes", [])) == 2

    def test_variable_without_type(self) -> None:
        """Variable without type should produce warning."""
        content = 'variable "name" {}'
        result = TerraformValidator(content, "variables.tf").validate_all()
        assert any(f.rule_id == "TF_VAR001" for f in result.findings)
