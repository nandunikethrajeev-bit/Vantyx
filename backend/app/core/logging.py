"""VANTYX Structured Logging.

Configures structured logging with automatic redaction of sensitive credentials,
tokens, passwords, and cookies.
"""

import logging
import re
import sys
from typing import Any, Dict

# Patterns for sensitive keys and tokens that must be redacted
SENSITIVE_PATTERNS = [
    re.compile(r"(password|passwd|pwd)\s*[:=]\s*['\"]?([^'\"\s,;}{]+)['\"]?", re.IGNORECASE),
    re.compile(r"(bearer\s+)(['\"]?[^'\"\s,;}{]+['\"]?)", re.IGNORECASE),
    re.compile(r"(token|jwt|auth)\s*[:=]\s*['\"]?([^'\"\s,;}{]+)['\"]?", re.IGNORECASE),
    re.compile(r"(secret|secret_key|api_key|apikey)\s*[:=]\s*['\"]?([^'\"\s,;}{]+)['\"]?", re.IGNORECASE),
    re.compile(r"(cookie|session)\s*[:=]\s*['\"]?([^'\"\s,;}{]+)['\"]?", re.IGNORECASE),
]

REDACTION_MASK = "[REDACTED]"


class RedactingFormatter(logging.Formatter):
    """Log formatter that automatically masks sensitive values in log messages."""

    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        redacted = original
        for pattern in SENSITIVE_PATTERNS:
            redacted = pattern.sub(r"\1: " + REDACTION_MASK, redacted)
        return redacted


def setup_logging(log_level: str = "INFO", environment: str = "development") -> logging.Logger:
    """Set up and configure the primary application logger."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Root vantyx logger
    logger = logging.getLogger("vantyx")
    logger.setLevel(level)

    # Avoid duplicate handlers if re-initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        log_format = (
            "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s"
        )
        formatter = RedactingFormatter(fmt=log_format, datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Standardize uvicorn loggers
    for uvicorn_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(uvicorn_logger_name)
        uv_logger.setLevel(level)

    return logger


logger = setup_logging()
