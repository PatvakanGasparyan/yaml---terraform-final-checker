"""
Structured logging setup.

Supports DEBUG, INFO, WARNING, ERROR levels via LOG_LEVEL env / settings.
"""

from __future__ import annotations

import logging
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_CONFIGURED = False


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure root logger once at application startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        fmt = (
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}'
        )
    else:
        fmt = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"

    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (call setup_logging first in entrypoints)."""
    return logging.getLogger(name)
