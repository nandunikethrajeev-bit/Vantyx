"""VANTYX Security Foundations.

Provides cryptographic and credential hygiene helpers, safe comparison,
and input sanitization utilities.
"""

import hmac
import secrets


def constant_time_compare(val_a: str, val_b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(val_a.encode("utf-8"), val_b.encode("utf-8"))


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a cryptographically strong URL-safe token."""
    return secrets.token_urlsafe(nbytes)


def is_production_safe_key(key: str) -> bool:
    """Validate that the secret key meets minimum entropy requirements for production."""
    if not key or len(key) < 32:
        return False
    insecure_defaults = [
        "development-insecure-secret-key-change-in-production-32chars",
        "replace-with-a-secure-random-secret-key-in-production",
        "secret",
        "changeme",
    ]
    return key not in insecure_defaults
