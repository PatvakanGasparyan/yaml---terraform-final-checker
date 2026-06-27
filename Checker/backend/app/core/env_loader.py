"""
Environment loader — single source of truth is a .env file.

On EC2, the file is downloaded from S3 when ENV_S3_BUCKET is set (via bootstrap.env
or instance environment). Application settings are read from the file only, not from
the process environment.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# Bootstrap variables (not stored in the S3 .env file)
S3_BOOTSTRAP_VARS = frozenset(
    {
        "ENV_S3_BUCKET",
        "ENV_S3_KEY",
        "ENV_FILE_PATH",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    }
)


def resolve_env_file_path() -> Path:
    """Return the path where the .env file is expected."""
    if explicit := os.environ.get("ENV_FILE_PATH"):
        return Path(explicit).expanduser().resolve()

    candidates = (
        Path.cwd() / ".env",
        Path("/app/.env"),
        Path(__file__).resolve().parents[3] / ".env",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    return (Path.cwd() / ".env").resolve()


def fetch_env_from_s3(target_path: Path) -> None:
    """Download .env from S3. Requires ENV_S3_BUCKET (and optional ENV_S3_KEY)."""
    bucket = os.environ.get("ENV_S3_BUCKET")
    if not bucket:
        return

    key = os.environ.get("ENV_S3_KEY", ".env")
    region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION")

    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required to fetch .env from S3") from exc

    target_path.parent.mkdir(parents=True, exist_ok=True)
    client_kwargs: dict[str, str] = {}
    if region:
        client_kwargs["region_name"] = region

    logger.info("Downloading s3://%s/%s -> %s", bucket, key, target_path)
    boto3.client("s3", **client_kwargs).download_file(bucket, key, str(target_path))
    logger.info("Downloaded .env from S3")


def ensure_env_file() -> Path:
    """
    Ensure the .env file exists on disk.

    1. Fetch from S3 when ENV_S3_BUCKET is configured
    2. Fall back to .env.example for local development only
    """
    path = resolve_env_file_path()

    if os.environ.get("ENV_S3_BUCKET"):
        fetch_env_from_s3(path)

    if path.is_file():
        return path

    example = path.parent / ".env.example"
    if example.is_file() and os.environ.get("APP_ENV", "development") == "development":
        shutil.copy(example, path)
        logger.warning("Created %s from .env.example for local development", path)
        return path

    raise FileNotFoundError(
        f"Required .env file not found at {path}. "
        "Upload .env to S3 and set ENV_S3_BUCKET, or copy .env.example to .env."
    )


def load_dotenv_file(path: Path | None = None) -> dict[str, str | None]:
    """Parse .env file into a dict (does not modify os.environ)."""
    env_path = path or ensure_env_file()
    if not env_path.is_file():
        raise FileNotFoundError(f".env file not found: {env_path}")
    return dotenv_values(env_path)


def main() -> int:
    """CLI: fetch and validate .env (used by EC2 deploy scripts)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        path = ensure_env_file()
        values = load_dotenv_file(path)
        logger.info("Loaded %d variables from %s", len(values), path)
        return 0
    except Exception as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
