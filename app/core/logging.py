"""Structured logging configuration."""

import logging
import sys
from typing import Any, Dict

import structlog

from app.core.config import settings


def configure_logging():
    """Configure structured logging."""
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # Configure structlog
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.is_prod:
        # Production format - JSON
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        # Development format - colored console
        shared_processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    structlog.configure(
        processors=shared_processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_structlog_logger(name: str = "ai-maga") -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger."""
    return structlog.get_logger(name)


class LoggerAdapter:
    """Adapter to implement LoggerProtocol."""

    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self._logger = logger

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(message, **kwargs)
