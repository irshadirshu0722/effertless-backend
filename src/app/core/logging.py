"""Structured logging configuration.

Uses Python's standard logging with JSON-compatible formatting for production.
See AGENTS.md additional guidelines on what must/must not be logged.
"""

import logging
import sys


class StructuredFormatter(logging.Formatter):
    """Log formatter that produces structured, grep-friendly output.

    In development: human-readable single-line format.
    In production: JSON-like key=value format for log aggregation.
    """

    def format(self, record: logging.LogRecord) -> str:
        record.asctime = self.formatTime(record, self.datefmt)
        # Add default extras if not present
        extra_fields = ""
        for key in ("request_id", "user_id", "session_id"):
            value = getattr(record, key, None)
            if value:
                extra_fields += f" {key}={value}"

        base = (
            f"{record.asctime} [{record.levelname}]"
            f" {record.name}: {record.getMessage()}{extra_fields}"
        )
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            base += f"\n{record.exc_text}"
        return base


def setup_logging(level: str = "INFO") -> None:
    """Configure application-wide logging.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = StructuredFormatter(
        fmt="%(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
