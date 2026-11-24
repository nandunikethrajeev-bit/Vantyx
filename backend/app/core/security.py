"""VANTYX Security Foundations & Cryptographic Hardening.

Provides credential hygiene helpers, constant-time comparison, token generation,
and robust encryption at rest using Fernet and MultiFernet.

Cryptographic Construction & Formal Specification:
Fernet specifies authenticated symmetric encryption:
- Symmetric Cipher: AES-128 in Cipher Block Chaining (CBC) mode with PKCS7 padding.
- Authentication & Integrity: HMAC using SHA-256 computed over:
    Version (0x80) || Timestamp (64-bit int) || IV (128-bit random) || Ciphertext
- Key Composition: A 32-byte (256-bit URL-safe base64) master key consisting of:
    * 16 bytes (128 bits) signing key for HMAC-SHA256
    * 16 bytes (128 bits) encryption key for AES-128-CBC
- Token Format:
    Version (1 byte) || Timestamp (8 bytes) || IV (16 bytes) || Ciphertext (variable, 16-byte aligned) || HMAC (32 bytes)
- MultiFernet Support:
    Decryption attempts the primary active key first, then iterates configured fallback
    keys in rotation order. Encryption strictly uses the active primary key.
"""

import base64
import hashlib
import hmac
import secrets
from typing import List, Optional, Tuple
from cryptography.fernet import Fernet, MultiFernet, InvalidToken

from app.core.config import settings
from app.core.logging import logger


class TokenEncryptionError(Exception):
    """Raised when token encryption fails."""
    pass


class TokenDecryptionError(Exception):
    """Raised when token decryption fails due to invalid token or mismatched key."""
    pass


def constant_time_compare(val_a: str, val_b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    return hmac.compare_digest(val_a.encode("utf-8"), val_b.encode("utf-8"))


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a cryptographically strong URL-safe token."""
    return secrets.token_urlsafe(nbytes)


def is_production_safe_key(key: str) -> bool:
    """Validate that the secret key meets minimum entropy requirements for production."""
    if not key or len(key.strip()) < 32:
        return False
    insecure_defaults = [
        "development-insecure-secret-key-change-in-production-32chars",
        "replace-with-a-secure-random-secret-key-in-production",
        "secret",
        "changeme",
    ]
    return key.strip() not in insecure_defaults


def _derive_fernet_key(raw_str: str) -> bytes:
    """Derive a valid 32-byte urlsafe-base64 key from any secret string."""
    raw_bytes = raw_str.strip().encode("utf-8")
    try:
        # Check if already a valid 32-byte base64 Fernet key
        Fernet(raw_bytes)
        return raw_bytes
    except Exception:
        return base64.urlsafe_b64encode(hashlib.sha256(raw_bytes).digest())


def _get_fernet() -> MultiFernet:
    """Retrieve or construct a MultiFernet cryptographic engine supporting rotation."""
    fernet_instances: List[Fernet] = []

    # 1. Primary active key
    primary_key = getattr(settings, "TOKEN_ENCRYPTION_KEY", "") or ""
    if primary_key and len(primary_key.strip()) > 0:
        fernet_instances.append(Fernet(_derive_fernet_key(primary_key)))
    else:
        # Fallback to deriving from application SECRET_KEY in dev/testing environments
        fernet_instances.append(Fernet(_derive_fernet_key(settings.SECRET_KEY)))

    # 2. Configured fallback rotation keys
    fallback_keys = getattr(settings, "TOKEN_ENCRYPTION_KEY_FALLBACKS", "") or ""
    if fallback_keys and len(fallback_keys.strip()) > 0:
        for fb in fallback_keys.split(","):
            fb_clean = fb.strip()
            if fb_clean:
                try:
                    fernet_instances.append(Fernet(_derive_fernet_key(fb_clean)))
                except Exception:
                    pass

    return MultiFernet(fernet_instances)


def encrypt_token(token: Optional[str]) -> Optional[str]:
    """Encrypt a sensitive OAuth token at rest using AES-128-CBC + HMAC-SHA256 (Fernet).
    
    Always encrypts with the active primary key.
    """
    if not token or not token.strip():
        return token
    try:
        f = _get_fernet()
        cipher_bytes = f.encrypt(token.encode("utf-8"))
        return cipher_bytes.decode("utf-8")
    except Exception as exc:
        logger.error(f"OAuth token encryption failed: {type(exc).__name__}")
        raise TokenEncryptionError("Failed to encrypt token: cryptographic operation failed") from exc


def decrypt_token(cipher_text: Optional[str]) -> Optional[str]:
    """Decrypt an encrypted OAuth token at rest.
    
    Supports MultiFernet rotation. Strictly raises TokenDecryptionError if the token
    is invalid, corrupted, or cannot be decrypted with any configured key.
    Never silently returns ciphertext as plaintext.
    """
    if not cipher_text or not cipher_text.strip():
        return cipher_text
    try:
        f = _get_fernet()
        plain_bytes = f.decrypt(cipher_text.encode("utf-8"))
        return plain_bytes.decode("utf-8")
    except InvalidToken as exc:
        logger.error("OAuth token decryption failed: invalid token signature or key mismatch")
        raise TokenDecryptionError("Failed to decrypt token: invalid or corrupted token") from exc
    except Exception as exc:
        logger.error(f"OAuth token decryption failed: {type(exc).__name__}")
        raise TokenDecryptionError(f"Failed to decrypt token: {type(exc).__name__}") from exc


def rotate_token(cipher_text: Optional[str]) -> Optional[str]:
    """Re-encrypt an existing token ciphertext using the active primary key."""
    if not cipher_text or not cipher_text.strip():
        return cipher_text
    try:
        f = _get_fernet()
        rotated_bytes = f.rotate(cipher_text.encode("utf-8"))
        return rotated_bytes.decode("utf-8")
    except Exception as exc:
        logger.error(f"Token re-encryption rotation failed: {type(exc).__name__}")
        raise TokenDecryptionError("Failed to rotate token: key mismatch or corrupted ciphertext") from exc


def validate_token_encryption_configuration(is_production: bool = False) -> Tuple[bool, str]:
    """Validate that a dedicated, production-safe TOKEN_ENCRYPTION_KEY is configured.
    
    In production environments, raises RuntimeError if TOKEN_ENCRYPTION_KEY is unset
    or insecure.
    """
    key = getattr(settings, "TOKEN_ENCRYPTION_KEY", "") or ""
    if not key or not key.strip():
        msg = (
            "Dedicated TOKEN_ENCRYPTION_KEY is not configured. "
            "Falling back to application SECRET_KEY is strictly prohibited in production."
        )
        if is_production:
            raise RuntimeError(msg)
        return False, msg

    if not is_production_safe_key(key):
        msg = "TOKEN_ENCRYPTION_KEY does not meet production entropy requirements (minimum 32 characters)."
        if is_production:
            raise RuntimeError(msg)
        return False, msg

    return True, "TOKEN_ENCRYPTION_KEY is configured and meets security requirements."
