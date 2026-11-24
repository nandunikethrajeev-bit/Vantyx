"""Unit tests for token encryption and credential hardening at rest."""

import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.security import (
    TokenDecryptionError,
    TokenEncryptionError,
    decrypt_token,
    encrypt_token,
    rotate_token,
    validate_token_encryption_configuration,
)


def test_token_encryption_and_decryption_roundtrip():
    """Verify that sensitive OAuth tokens can be encrypted and decrypted accurately."""
    raw_token = "ya29.a0ARrdaM_test_oauth_access_token_sample_12345"
    encrypted = encrypt_token(raw_token)

    assert encrypted is not None
    assert encrypted != raw_token
    assert len(encrypted) > len(raw_token)

    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token


def test_undecryptable_token_raises_exception():
    """Verify that undecryptable or invalid tokens strictly raise TokenDecryptionError.
    
    Protects against silently treating encrypted or corrupted data as plaintext.
    """
    invalid_token = "not_a_valid_fernet_token_string_12345"
    with pytest.raises(TokenDecryptionError) as exc_info:
        decrypt_token(invalid_token)
    assert "Failed to decrypt token" in str(exc_info.value)


def test_none_and_empty_token_handling():
    """Verify that None and empty strings pass through safely."""
    assert encrypt_token(None) is None
    assert encrypt_token("") == ""
    assert decrypt_token(None) is None
    assert decrypt_token("") == ""


def test_custom_encryption_key(monkeypatch):
    """Verify encryption works with explicit TOKEN_ENCRYPTION_KEY."""
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", key)
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY_FALLBACKS", "")

    token = "ya29.live_production_token"
    enc = encrypt_token(token)
    assert enc != token
    assert decrypt_token(enc) == token


def test_multifernet_key_rotation(monkeypatch):
    """Verify seamless key rotation using MultiFernet.
    
    Tokens encrypted with an older key remain decryptable via fallback keys
    and can be re-encrypted (rotated) with the active primary key.
    """
    old_key = Fernet.generate_key().decode("utf-8")
    new_key = Fernet.generate_key().decode("utf-8")

    # 1. Encrypt with old key as primary
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", old_key)
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY_FALLBACKS", "")
    token = "ya29.secret_refresh_token_to_rotate"
    old_ciphertext = encrypt_token(token)

    # 2. Promote new key to primary and configure old key as fallback
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", new_key)
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY_FALLBACKS", old_key)

    # Old ciphertext must still decrypt cleanly via fallback
    decrypted = decrypt_token(old_ciphertext)
    assert decrypted == token

    # Rotate ciphertext: re-encrypts under active primary key (new_key)
    new_ciphertext = rotate_token(old_ciphertext)
    assert new_ciphertext != old_ciphertext

    # 3. Demote old key entirely (no fallback)
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY_FALLBACKS", "")
    # New ciphertext decrypts under new_key alone
    assert decrypt_token(new_ciphertext) == token
    # Old ciphertext without fallback now correctly raises TokenDecryptionError
    with pytest.raises(TokenDecryptionError):
        decrypt_token(old_ciphertext)


def test_production_configuration_validation(monkeypatch):
    """Verify startup validation for production encryption keys."""
    # 1. Insecure default key in production raises RuntimeError
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", "")
    with pytest.raises(RuntimeError) as exc_info:
        validate_token_encryption_configuration(is_production=True)
    assert "strictly prohibited in production" in str(exc_info.value)

    # 2. Valid key passes in production
    valid_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr(settings, "TOKEN_ENCRYPTION_KEY", valid_key)
    is_valid, msg = validate_token_encryption_configuration(is_production=True)
    assert is_valid is True
