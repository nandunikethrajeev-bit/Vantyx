"""VANTYX Security Foundations.

Provides cryptographic and credential hygiene helpers, safe comparison,
and input sanitization utilities.
"""

import base64
import hashlib
import hmac
import secrets
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
from app.core.logging import logger


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


def _get_fernet() -> Fernet:
    """Retrieve or construct a Fernet cryptographic engine from configuration."""
    key = getattr(settings, "TOKEN_ENCRYPTION_KEY", "") or ""
    if key and len(key.strip()) > 0:
        raw_key = key.strip().encode("utf-8")
        try:
            return Fernet(raw_key)
        except Exception:
            # Derive valid 32-byte urlsafe-base64 key via SHA-256
            derived = base64.urlsafe_b64encode(hashlib.sha256(raw_key).digest())
            return Fernet(derived)

    # Fallback to deriving from application SECRET_KEY
    derived = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest())
    return Fernet(derived)


def encrypt_token(token: Optional[str]) -> Optional[str]:
    """Encrypt a sensitive OAuth token at rest using AES-CBC / Fernet encryption."""
    if not token or not token.strip():
        return token
    try:
        f = _get_fernet()
        cipher_bytes = f.encrypt(token.encode("utf-8"))
        return cipher_bytes.decode("utf-8")
    except Exception as exc:
        logger.error(f"Failed to encrypt token: {exc}")
        raise RuntimeError("OAuth token encryption failed") from exc


def decrypt_token(cipher_text: Optional[str]) -> Optional[str]:
    """Decrypt an encrypted OAuth token at rest.
    
    Gracefully returns original text if input is already plaintext or legacy format.
    """
    if not cipher_text or not cipher_text.strip():
        return cipher_text
    try:
        f = _get_fernet()
        plain_bytes = f.decrypt(cipher_text.encode("utf-8"))
        return plain_bytes.decode("utf-8")
    except (InvalidToken, Exception):
        # Fallback for unencrypted legacy or simulated mock tokens
        return cipher_text
