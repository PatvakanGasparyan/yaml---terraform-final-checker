"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest

# Point tests at Checker/.env (created from .env.example in CI and local dev)
_checker_env = Path(__file__).resolve().parents[2] / ".env"
if _checker_env.is_file():
    os.environ.setdefault("ENV_FILE_PATH", str(_checker_env))
