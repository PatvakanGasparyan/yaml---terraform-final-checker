"""
YTV CLI — enterprise IaC validator command-line interface.

Usage:
  ytv validate -f main.tf
  ytv scan -f deploy.yaml --security
  ytv fix -f config.yaml -o fixed.yaml
  ytv report -f main.tf --format sarif -o report.sarif
"""

from __future__ import annotations

import asyncio
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer

from app.logging.setup import get_logger, setup_logging
from app.reporting.formats import ReportFormat, generate_report
from app.schemas import ValidationRequest, ValidationResponse
from app.services.validation_service import ValidationService

app = typer.Typer(
    name="ytv",
    help="YAML & Terraform AI Validator — enterprise DevOps CLI",
    no_args_is_help=True,
)
logger = get_logger(__name__)


class OutputFormat(str, Enum):
    json = "json"
    yaml = "yaml"
    markdown = "markdown"
    html = "html"
    sarif = "sarif"
    junit = "junit"
    text = "text"


def _read_file(path: Path) -> tuple[str, str]:
    content = path.read_text(encoding="utf-8")
    return content, str(path.name)


def _run_validation(
    content: str,
    file_path: str,
    validation_type: str,
    include_ai: bool,
    include_security: bool,
    auto_fix: bool,
) -> ValidationResponse:
    """Run validation pipeline without DB persistence (CLI mode)."""
    from app.services.validation_service import ValidationService

    class _NoDbSession:
        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

        def add(self, *_: object) -> None:
            pass

    service = ValidationService(_NoDbSession())  # type: ignore[arg-type]
    request = ValidationRequest(
        content=content,
        file_path=file_path,
        validation_type=validation_type,
        include_ai_analysis=include_ai,
        include_security_scan=include_security,
        auto_fix=auto_fix,
    )

    async def _execute() -> ValidationResponse:
        return await service.validate_cli(request)

    return asyncio.run(_execute())


def _print_or_save(result: ValidationResponse, fmt: OutputFormat, output: Path | None) -> None:
    if fmt == OutputFormat.text:
        text = result.summary or "Done"
        typer.echo(text)
        if result.findings:
            for f in result.findings:
                typer.echo(f"  [{f.severity}] L{f.line_number or '?'}: {f.message}")
        return

    report_fmt = ReportFormat(fmt.value)
    body, _ = generate_report(result, report_fmt)
    if output:
        output.write_text(body, encoding="utf-8")
        typer.echo(f"Report written to {output}")
    else:
        typer.echo(body)


@app.command()
def validate(
    file: Annotated[Path, typer.Option("--file", "-f", help="Path to YAML or Terraform file")],
    type: Annotated[str, typer.Option("--type", "-t", help="auto|yaml|terraform")] = "auto",
    ai: Annotated[bool, typer.Option("--ai/--no-ai", help="Enable AI analysis")] = False,
    security: Annotated[bool, typer.Option("--security/--no-security")] = True,
    format: Annotated[OutputFormat, typer.Option("--format", "-o")] = OutputFormat.text,
    output: Annotated[Optional[Path], typer.Option("--output", "-O")] = None,
) -> None:
    """Validate a configuration file."""
    setup_logging()
    content, name = _read_file(file)
    result = _run_validation(content, name, type, ai, security, auto_fix=False)
    _print_or_save(result, format, output)
    if result.error_count > 0:
        raise typer.Exit(code=1)


@app.command()
def scan(
    file: Annotated[Path, typer.Option("--file", "-f")],
    security: Annotated[bool, typer.Option("--security/--no-security")] = True,
    ai: Annotated[bool, typer.Option("--ai/--no-ai")] = True,
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.json,
    output: Annotated[Optional[Path], typer.Option("--output", "-O")] = None,
) -> None:
    """Deep scan with security and optional AI review."""
    setup_logging()
    content, name = _read_file(file)
    result = _run_validation(content, name, "auto", ai, security, auto_fix=False)
    _print_or_save(result, format, output)
    raise typer.Exit(code=1 if result.error_count else 0)


@app.command()
def fix(
    file: Annotated[Path, typer.Option("--file", "-f")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Write fixed file")],
    type: Annotated[str, typer.Option("--type", "-t")] = "auto",
    ai: Annotated[bool, typer.Option("--ai/--no-ai")] = True,
) -> None:
    """Auto-fix validation issues and write corrected file."""
    setup_logging()
    content, name = _read_file(file)
    result = _run_validation(content, name, type, ai, True, auto_fix=True)
    fixed = result.corrected_content or content
    output.write_text(fixed, encoding="utf-8")
    typer.echo(f"Fixed content written to {output} ({result.error_count} errors addressed)")
    raise typer.Exit(code=1 if result.error_count and not result.corrected_content else 0)


@app.command("report")
def report_cmd(
    file: Annotated[Path, typer.Option("--file", "-f")],
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.markdown,
    output: Annotated[Optional[Path], typer.Option("--output", "-O")] = None,
) -> None:
    """Generate validation report (JSON, SARIF, JUnit, HTML, Markdown)."""
    setup_logging()
    content, name = _read_file(file)
    result = _run_validation(content, name, "auto", False, True, auto_fix=False)
    _print_or_save(result, format, output)


@app.command()
def explain(
    file: Annotated[Path, typer.Option("--file", "-f")],
) -> None:
    """AI line-by-line explanation (requires OPENAI_API_KEY)."""
    setup_logging()
    content, name = _read_file(file)
    result = _run_validation(content, name, "auto", True, False, auto_fix=False)
    for exp in result.ai_explanations:
        typer.echo(f"L{exp.line_number} [{exp.risk_level}]: {exp.explanation}")


@app.command()
def summary(
    file: Annotated[Path, typer.Option("--file", "-f")],
) -> None:
    """Print one-line validation summary."""
    content, name = _read_file(file)
    result = _run_validation(content, name, "auto", False, True, auto_fix=False)
    typer.echo(result.summary or "OK")


@app.command()
def doctor() -> None:
    """Check environment, dependencies, and configuration."""
    setup_logging()
    from app.core.config import get_settings

    s = get_settings()
    checks: list[tuple[str, bool, str]] = []

    checks.append(("SECRET_KEY set", s.SECRET_KEY != "change-me-in-production-use-openssl-rand-hex-32", "Set SECRET_KEY in .env"))
    checks.append(("OpenAI configured", bool(s.OPENAI_API_KEY) or s.AI_PROVIDER != "openai", "Optional: set OPENAI_API_KEY"))
    checks.append(("DB engine", True, f"DB_ENGINE={s.DB_ENGINE}"))

    import shutil

    for tool in ("terraform", "checkov", "tfsec", "trivy"):
        found = shutil.which(tool) is not None
        checks.append((f"{tool} CLI", found, "Install for extended scanning" if not found else "OK"))

    ok = True
    for name, passed, hint in checks:
        status = typer.style("OK", fg="green") if passed else typer.style("WARN", fg="yellow")
        typer.echo(f"  [{status}] {name} — {hint}")
        if name.startswith("SECRET") and not passed:
            ok = False

    raise typer.Exit(code=0 if ok else 1)


@app.command()
def version() -> None:
    """Show CLI and platform version."""
    from app.core.config import get_settings

    typer.echo(f"ytv {get_settings().APP_VERSION}")


@app.command()
def plugins() -> None:
    """List registered validator plugins."""
    from app.plugins.registry import get_plugin_registry

    for p in get_plugin_registry().list_plugins():
        typer.echo(json.dumps(p))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
