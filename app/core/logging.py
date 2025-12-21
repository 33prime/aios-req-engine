"""Structured logging configuration for AIOS Req Engine."""

import logging
import sys
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON-like structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured output."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }

        # Add run_id if present in extra
        if hasattr(record, "run_id"):
            log_data["run_id"] = record.run_id

        # Add any other extra fields
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Format as key=value pairs for readability
        parts = [f"{k}={v}" for k, v in log_data.items()]
        return " ".join(parts)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)

        # Set level based on environment
        try:
            from app.core.config import get_settings

            settings = get_settings()
            if settings.REQ_ENGINE_ENV == "dev":
                logger.setLevel(logging.DEBUG)
            else:
                logger.setLevel(logging.INFO)
        except Exception:
            # Default to INFO if settings not available
            logger.setLevel(logging.INFO)

    return logger


def log_with_context(logger: logging.Logger, level: int, msg: str, **kwargs: Any) -> None:
    """
    Log with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (logging.INFO, etc.)
        msg: Log message
        **kwargs: Additional context fields (e.g., run_id)
    """
    extra = {"extra_data": kwargs}
    if "run_id" in kwargs:
        extra["run_id"] = kwargs.pop("run_id")
        extra["extra_data"] = kwargs

    logger.log(level, msg, extra=extra)
