"""Structured logging configuration."""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any

import structlog


def sanitize_value(key: str, value: Any) -> Any:
    """Sanitize sensitive values from logs.

    Args:
        key: Key name
        value: Value to potentially sanitize

    Returns:
        Original value or [REDACTED] if sensitive
    """
    sensitive_keys = {
        "api_key",
        "token",
        "password",
        "secret",
        "authorization",
        "bot_token",
        "api-key",
        "tracker_api_key",
        "telegram_bot_token",
    }

    if any(sensitive in key.lower() for sensitive in sensitive_keys):
        if isinstance(value, str) and len(value) > 8:
            return f"{value[:4]}...{value[-4:]}"
        return "[REDACTED]"
    return value


def sanitize_event_dict(_, __, event_dict):
    """Processor to sanitize event dict."""
    for key, value in event_dict.items():
        event_dict[key] = sanitize_value(key, value)
    return event_dict


def setup_logging(
    log_level: str = "INFO", log_file: str = None, enable_rotation: bool = True
):
    """Configure structured logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file (None for stdout only)
        enable_rotation: Enable log rotation for file logging
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        sanitize_event_dict,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Add appropriate renderer based on output
    if sys.stderr.isatty():
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Setup standard logging for libraries
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Add file handler if requested
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        if enable_rotation:
            # Rotate when file reaches 10MB, keep 5 backups
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
        else:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")

        file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        file_handler.setFormatter(logging.Formatter("%(message)s"))

        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

    # Suppress overly verbose library logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)


def get_logger(name: str = None):
    """Get a structured logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)
