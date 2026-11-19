"""Unit tests for structured logging and sensitive credential masking."""

import logging
from app.core.logging import RedactingFormatter, REDACTION_MASK


def test_sensitive_credentials_redaction():
    """Verify that sensitive values in logs are safely masked."""
    formatter = RedactingFormatter(fmt="%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="User authenticated password='SuperSecretPassword123' token: Bearer eyJhbGciOiJIUz",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "SuperSecretPassword123" not in formatted
    assert "eyJhbGciOiJIUz" not in formatted
    assert REDACTION_MASK in formatted


def test_api_key_redaction():
    """Verify api_key and secrets are masked."""
    formatter = RedactingFormatter(fmt="%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Connecting to provider with api_key=AIzaSyD-123456789 and cookie: session=xyz987",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    assert "AIzaSyD-123456789" not in formatted
    assert "xyz987" not in formatted
    assert REDACTION_MASK in formatted
