"""
Multi-format validation report generators.

Supports JSON, YAML, Markdown, HTML, SARIF 2.1, and JUnit XML.
"""

from __future__ import annotations

import html
import json
import xml.etree.ElementTree as ET
from enum import Enum
from typing import Any

import yaml

from app.schemas import ValidationResponse


class ReportFormat(str, Enum):
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    HTML = "html"
    SARIF = "sarif"
    JUNIT = "junit"


def generate_report(result: ValidationResponse, fmt: ReportFormat) -> tuple[str, str]:
    """
    Generate report body and MIME type.

    Returns (content, media_type).
    """
    payload = result.model_dump(mode="json")
    generators = {
        ReportFormat.JSON: _json_report,
        ReportFormat.YAML: _yaml_report,
        ReportFormat.MARKDOWN: _markdown_report,
        ReportFormat.HTML: _html_report,
        ReportFormat.SARIF: _sarif_report,
        ReportFormat.JUNIT: _junit_report,
    }
    return generators[fmt](payload)


def _json_report(payload: dict[str, Any]) -> tuple[str, str]:
    return json.dumps(payload, indent=2, default=str), "application/json"


def _yaml_report(payload: dict[str, Any]) -> tuple[str, str]:
    return yaml.dump(payload, default_flow_style=False, sort_keys=False), "application/x-yaml"


def _markdown_report(payload: dict[str, Any]) -> tuple[str, str]:
    lines = [
        "# Validation Report",
        "",
        f"- **Status:** {payload.get('status')}",
        f"- **Type:** {payload.get('validation_type')}",
        f"- **Duration:** {payload.get('duration_ms')} ms",
        f"- **Summary:** {payload.get('summary', 'N/A')}",
        "",
        "## Findings",
        "",
    ]
    for f in payload.get("findings", []):
        sev = f.get("severity", "")
        msg = f.get("message", "")
        line = f.get("line_number")
        loc = f" (L{line})" if line else ""
        lines.append(f"- **[{sev}]**{loc} {msg}")
        if f.get("corrected_code"):
            lines.append(f"  - Fix: `{f['corrected_code']}`")

    lines.extend(["", "## Security", ""])
    for s in payload.get("security_findings", []):
        lines.append(f"- **[{s.get('severity')}]** {s.get('title')} ({s.get('scanner')})")

    lines.extend(["", "## AI Analysis", ""])
    for a in payload.get("ai_explanations", []):
        lines.append(f"- **L{a.get('line_number')}:** {a.get('explanation')}")

    if payload.get("corrected_content"):
        lines.extend(["", "## Corrected Content", "", "```", payload["corrected_content"], "```"])

    return "\n".join(lines), "text/markdown"


def _html_report(payload: dict[str, Any]) -> tuple[str, str]:
    findings_rows = "".join(
        f"<tr><td>{html.escape(str(f.get('severity')))}</td>"
        f"<td>{f.get('line_number') or ''}</td>"
        f"<td>{html.escape(f.get('message', ''))}</td></tr>"
        for f in payload.get("findings", [])
    )
    body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Validation Report</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;max-width:960px}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ddd;padding:8px}}
th{{background:#f4f4f5;text-align:left}}
.badge{{display:inline-block;padding:2px 8px;border-radius:4px;background:#e0e7ff}}
</style></head><body>
<h1>Validation Report</h1>
<p><span class="badge">{html.escape(str(payload.get('status')))}</span>
 {html.escape(str(payload.get('validation_type')))} · {payload.get('duration_ms')} ms</p>
<p>{html.escape(str(payload.get('summary', '')))}</p>
<h2>Findings</h2>
<table><tr><th>Severity</th><th>Line</th><th>Message</th></tr>{findings_rows or '<tr><td colspan="3">None</td></tr>'}</table>
</body></html>"""
    return body, "text/html"


def _sarif_report(payload: dict[str, Any]) -> tuple[str, str]:
    rules: dict[str, dict] = {}
    results = []
    for f in payload.get("findings", []):
        rule_id = f.get("rule_id") or f.get("category") or "YTV001"
        rules[rule_id] = {
            "id": rule_id,
            "name": f.get("category", "validation"),
            "shortDescription": {"text": f.get("category", "validation")},
        }
        results.append(
            {
                "ruleId": rule_id,
                "level": _sarif_level(f.get("severity", "informational")),
                "message": {"text": f.get("message", "")},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": f.get("file_path", "input")},
                            "region": {"startLine": f.get("line_number") or 1},
                        }
                    }
                ],
            }
        )

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "yaml-terraform-validator",
                        "version": "1.0.0",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2), "application/sarif+json"


def _junit_report(payload: dict[str, Any]) -> tuple[str, str]:
    testsuite = ET.Element(
        "testsuite",
        name="validation",
        tests=str(len(payload.get("findings", [])) + 1),
        failures=str(payload.get("error_count", 0)),
        errors="0",
    )
    tc = ET.SubElement(testsuite, "testcase", name="validation-run", classname="ytv")
    if payload.get("error_count", 0) > 0:
        fail = ET.SubElement(tc, "failure", message=payload.get("summary", "Validation failed"))
        fail.text = payload.get("summary", "")
    for i, f in enumerate(payload.get("findings", [])):
        case = ET.SubElement(
            testsuite,
            "testcase",
            name=f.get("rule_id") or f"finding-{i}",
            classname=f.get("category", "validation"),
        )
        if f.get("severity") in ("critical", "high"):
            fl = ET.SubElement(case, "failure", message=f.get("message", ""))
            fl.text = f.get("message", "")
    return ET.tostring(testsuite, encoding="unicode", xml_declaration=True), "application/xml"


def _sarif_level(severity: str) -> str:
    return {
        "critical": "error",
        "high": "error",
        "medium": "warning",
        "low": "note",
        "informational": "note",
    }.get(severity.lower(), "warning")
