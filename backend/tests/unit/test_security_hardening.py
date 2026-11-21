"""Unit tests for token encryption and credential hardening at rest."""

import pytest
from app.core.config import Settings
from app.core.security import encrypt_token, decrypt_token, _get_fernet


def test_token_encryption_and_decryption_roundtrip():
    """Verify that sensitive OAuth tokens can be encrypted and decrypted accurately."""
    raw_token = "ya29.a0ARrdaM_test_oauth_access_token_sample_12345"
    encrypted = encrypt_token(raw_token)

    assert encrypted is not None
    assert encrypted != raw_token
    assert len(encrypted) > len(raw_token)

    decrypted = decrypt_token(encrypted)
    assert decrypted == raw_token


def test_legacy_unencrypted_token_fallback():
    """Verify that unencrypted legacy tokens are gracefully returned without crashing."""
    legacy_token = "legacy_unencrypted_mock_token_abc"
    result = decrypt_token(legacy_token)
    assert result == legacy_token


def test_none_and_empty_token_handling():
    """Verify that None and empty strings pass through safely."""
    assert encrypt_token(None) is None
    assert encrypt_token("") == ""
    assert decrypt_token(None) is None
    assert decrypt_token("") == ""


def test_custom_encryption_key(monkeypatch):
    """Verify encryption works with explicit TOKEN_ENCRYPTION_KEY."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr("app.core.config.settings.TOKEN_ENCRYPTION_KEY", key)

    token = "ya29.live_production_token"
    enc = encrypt_token(token)
    assert enc != token
    assert decrypt_token(enc) == token
