"""
AI analysis engine with OpenAI-compatible API architecture.

Supports OpenAI, Azure OpenAI, Ollama, and local LLMs for
line-by-line code explanation, risk analysis, and fix generation.
"""

import json
import re
from typing import Any

from app.ai.openai_client import OpenAIClient, OpenAIClientError
from app.core.config import get_settings
from app.schemas import LineExplanation, SeverityLevel, ValidationFinding

settings = get_settings()
logger = __import__("logging").getLogger(__name__)


class AIAnalyzer:
    """
    AI-powered code analysis engine.

    Provides line explanations, risk analysis, improvement suggestions,
    security recommendations, cost optimization, and corrected versions.
    """

    def __init__(self) -> None:
        """Initialize AI client based on configured provider."""
        self._client = OpenAIClient()
        self.provider = self._client.provider
        self.model = self._client.model

    def _create_client(self) -> None:
        """Deprecated — use OpenAIClient."""
        return None

    def _get_model(self) -> str:
        return self.model

    async def analyze_code(
        self,
        content: str,
        file_path: str,
        language: str = "yaml",
        response_language: str = "en",
    ) -> dict[str, Any]:
        """
        Perform comprehensive AI analysis on code.

        Args:
            content: Source code content.
            file_path: File path for context.
            language: Code language (yaml, terraform, python).
            response_language: Language for AI responses (en, ru, hy).

        Returns:
            Dict with explanations, risk_analysis, suggestions, corrections.
        """
        if not self._client.is_available:
            return self._fallback_analysis(content, file_path, language)

        lang_names = {"en": "English", "ru": "Russian", "hy": "Armenian"}
        response_lang = lang_names.get(response_language, "English")

        default_system_prompt = f"""You are an expert DevOps and Infrastructure-as-Code analyst (2025 standards).
Analyze the provided {language} configuration file line by line.
Respond in {response_lang}.

For each significant line, provide:
- line_number
- code (the actual line)
- explanation (what it does and why it matters)
- risk_level (critical/high/medium/low/informational)
- recommendation (actionable fix if applicable)

Also provide:
- risk_analysis: overall risk summary
- improvements: list of improvement suggestions
- security_recommendations: CIS/NIST-aligned security fixes
- cost_optimizations: cloud cost saving suggestions
- corrected_content: full corrected version if fixes needed

Focus on: least privilege, secrets management, network exposure, resource limits, and IaC best practices.
Return valid JSON only."""

        system_prompt = settings.AI_SYSTEM_PROMPT.strip() or default_system_prompt

        user_prompt = f"File: {file_path}\nLanguage: {language}\n\n```\n{content}\n```"

        try:
            result = await self._client.analyze_json(system_prompt, user_prompt)
            result["ai_model"] = self.model
            result.setdefault("tokens_used", 0)
            return result
        except OpenAIClientError:
            logger.warning("AI analysis failed; using rule-based fallback")
            return self._fallback_analysis(content, file_path, language)

    async def explain_lines(
        self,
        content: str,
        file_path: str,
        language: str = "yaml",
    ) -> list[LineExplanation]:
        """
        Generate line-by-line explanations.

        Args:
            content: Source code.
            file_path: File path.
            language: Code language.

        Returns:
            List of LineExplanation objects.
        """
        analysis = await self.analyze_code(content, file_path, language)
        explanations: list[LineExplanation] = []

        for item in analysis.get("explanations", analysis.get("lines", [])):
            if isinstance(item, dict):
                explanations.append(
                    LineExplanation(
                        line_number=item.get("line_number", 0),
                        code=item.get("code", ""),
                        explanation=item.get("explanation", ""),
                        risk_level=SeverityLevel(
                            item.get("risk_level", "informational").lower()
                        ),
                        recommendation=item.get("recommendation"),
                    )
                )

        # Fallback: generate basic explanations from content
        if not explanations:
            explanations = self._generate_basic_explanations(content, language)

        return explanations

    async def generate_fixes(
        self,
        content: str,
        findings: list[ValidationFinding],
        language: str = "yaml",
    ) -> tuple[str | None, list[ValidationFinding]]:
        """
        Generate corrected content based on validation findings.

        Args:
            content: Original content.
            findings: Validation findings with corrections.
            language: Code language.

        Returns:
            Tuple of (corrected_content, updated_findings_with_corrections).
        """
        # Apply inline corrections from findings first
        lines = content.splitlines()
        updated_findings = list(findings)

        for finding in findings:
            if finding.corrected_code and finding.line_number and finding.original_code:
                idx = finding.line_number - 1
                if 0 <= idx < len(lines) and finding.original_code.strip() in lines[idx]:
                    lines[idx] = finding.corrected_code

        corrected = "\n".join(lines)

        # Try AI for comprehensive fix if client available
        if self._client.is_available and any(
            f.severity in (SeverityLevel.CRITICAL, SeverityLevel.HIGH) for f in findings
        ):
            try:
                analysis = await self.analyze_code(content, "fix", language)
                if analysis.get("corrected_content"):
                    corrected = analysis["corrected_content"]
            except Exception:
                pass

        return corrected if corrected != content else None, updated_findings

    def _fallback_analysis(
        self,
        content: str,
        file_path: str,
        language: str,
    ) -> dict[str, Any]:
        """
        Rule-based fallback when AI provider is unavailable.

        Provides basic analysis without external API calls.
        """
        lines = content.splitlines()
        explanations = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            explanation = self._explain_line_heuristic(stripped, language)
            risk = self._assess_line_risk(stripped, language)

            explanations.append({
                "line_number": i,
                "code": line,
                "explanation": explanation,
                "risk_level": risk.value,
                "recommendation": self._get_recommendation(stripped, language, risk),
            })

        return {
            "explanations": explanations,
            "risk_analysis": f"Analyzed {len(lines)} lines using rule-based engine (AI unavailable)",
            "improvements": self._get_improvements(content, language),
            "security_recommendations": self._get_security_recommendations(content, language),
            "cost_optimizations": [],
            "corrected_content": None,
            "ai_model": "rule-based-fallback",
            "tokens_used": 0,
        }

    def _explain_line_heuristic(self, line: str, language: str) -> str:
        """Generate heuristic explanation for a line."""
        if language == "yaml":
            if line.startswith("apiVersion:"):
                return "Defines the Kubernetes API version for this resource"
            if line.startswith("kind:"):
                return "Specifies the Kubernetes resource type"
            if line.startswith("- "):
                return "List item in YAML array"
            if ":" in line:
                key = line.split(":")[0].strip()
                return f"Configuration property: {key}"
        elif language == "terraform":
            if line.startswith("resource "):
                return "Defines an infrastructure resource to be managed by Terraform"
            if line.startswith("variable "):
                return "Declares an input variable for module configuration"
            if line.startswith("provider "):
                return "Configures a cloud/infrastructure provider"
            if line.startswith("module "):
                return "References an external Terraform module"

        return f"Configuration line: {line[:80]}"

    def _assess_line_risk(self, line: str, language: str) -> SeverityLevel:
        """Assess risk level of a line using heuristics."""
        high_risk_patterns = [
            r"0\.0\.0\.0/0",
            r"privileged.*true",
            r"password\s*=",
            r"secret\s*=",
            r"public-read",
        ]
        for pattern in high_risk_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return SeverityLevel.HIGH

        medium_patterns = [r"http://", r"allowPrivilegeEscalation.*true"]
        for pattern in medium_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return SeverityLevel.MEDIUM

        return SeverityLevel.INFORMATIONAL

    def _get_recommendation(self, line: str, language: str, risk: SeverityLevel) -> str | None:
        """Get recommendation based on line content and risk."""
        if risk == SeverityLevel.HIGH:
            if "0.0.0.0/0" in line:
                return "Restrict CIDR block to specific IP ranges"
            if "password" in line.lower() or "secret" in line.lower():
                return "Use secret manager or environment variables"
        return None

    def _generate_basic_explanations(self, content: str, language: str) -> list[LineExplanation]:
        """Generate basic line explanations without AI."""
        explanations = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped:
                explanations.append(
                    LineExplanation(
                        line_number=i,
                        code=line,
                        explanation=self._explain_line_heuristic(stripped, language),
                        risk_level=self._assess_line_risk(stripped, language),
                        recommendation=self._get_recommendation(
                            stripped, language, self._assess_line_risk(stripped, language)
                        ),
                    )
                )
        return explanations

    def _get_improvements(self, content: str, language: str) -> list[str]:
        """Get general improvement suggestions."""
        improvements = []
        if "\t" in content:
            improvements.append("Replace tab characters with spaces for YAML consistency")
        if language == "terraform" and "terraform {" not in content:
            improvements.append("Add terraform configuration block with required_version")
        return improvements

    def _get_security_recommendations(self, content: str, language: str) -> list[str]:
        """Get security recommendations."""
        recommendations = []
        if re.search(r'password\s*=\s*"', content, re.IGNORECASE):
            recommendations.append("Remove hardcoded passwords; use AWS Secrets Manager or similar")
        if "0.0.0.0/0" in content:
            recommendations.append("Review and restrict open network access rules")
        return recommendations
