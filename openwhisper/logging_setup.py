"""Structured logging setup. All modules get a child logger via `get_logger`.

Keeping this centralized lets us swap formatters (e.g. JSON in production)
without touching call sites.

Security: Uses rotating log files with size limits and automatic deletion
of old logs to prevent unbounded growth and reduce exposure of historical
dictation metadata.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import log_file_path

# Security: Limit log file size and retention
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB per file
LOG_BACKUP_COUNT = 3  # Keep 3 backup files (total ~20 MB max)

_configured = False


def setup_logging(level: int = logging.INFO) -> None:
    """Idempotent root logger setup. Writes to a rotating log file AND stderr."""
    global _configured
    if _configured:
        return

    root = logging.getLogger("openwhisper")
    root.setLevel(level)
    root.propagate = False

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname).1s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    stream = logging.StreamHandler(stream=sys.stderr)
    stream.setFormatter(fmt)
    root.addHandler(stream)

    try:
        log_path: Path = log_file_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Security: Use rotating handler to limit log size and auto-delete old logs
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except Exception as exc:  # pragma: no cover — logging must never crash the app
        root.warning("Could not open log file: %s", exc)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the `openwhisper` namespace."""
    return logging.getLogger(f"openwhisper.{name}")
