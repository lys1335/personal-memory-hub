"""Logging configuration.

Uses structlog for structured JSON logging.
Log level is read from settings (APP_LOG_LEVEL).
"""

from __future__ import annotations

import logging
from typing import Any

import structlog

from backend.shared.infrastructure.config.settings import get_settings


def configure_logging() -> None:
    """Configure structlog with a JSON console handler.

    Called once at application startup.  Idempotent: safe to call
    multiple times — only the first call has any effect.
    """
    s = get_settings()
    level = getattr(logging, s.LOG_LEVEL.value, logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """Return a structlog bound logger.

    Args:
        name: Logger name (typically ``__name__``).

    Returns:
        A pre-configured structlog bound logger.
    """
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
