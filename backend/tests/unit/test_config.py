"""Unit tests for configuration management and security safeguards."""

import pytest
from app.core.config import Settings
from app.core.security import constant_time_compare, generate_secure_token, is_production_safe_key


def test_default_settings():
    """Verify default development configuration provides safe defaults."""
    cfg = Settings()
    assert cfg.PROJECT_NAME == "VANTYX"
    assert cfg.ENVIRONMENT in ("development", "test", "staging", "production")
    assert cfg.API_V1_PREFIX == "/api/v1"
    assert "http://localhost:5173" in cfg.CORS_ORIGINS
    assert "vantyx" in cfg.async_database_url
    assert "postgresql+asyncpg://" in cfg.async_database_url


def test_cors_origins_parsing():
    """Verify that comma-separated strings are parsed into lists."""
    cfg = Settings(CORS_ORIGINS="http://example.com,https://app.vantyx.ai")
    assert isinstance(cfg.CORS_ORIGINS, list)
    assert len(cfg.CORS_ORIGINS) == 2
    assert "http://example.com" in cfg.CORS_ORIGINS
    assert "https://app.vantyx.ai" in cfg.CORS_ORIGINS


def test_security_helpers():
    """Verify constant time comparison and token generation."""
    t1 = generate_secure_token(32)
    t2 = generate_secure_token(32)
    assert len(t1) > 20
    assert constant_time_compare(t1, t1) is True
    assert constant_time_compare(t1, t2) is False

    # Production key security checks
    assert is_production_safe_key("short") is False
    assert is_production_safe_key("development-insecure-secret-key-change-in-production-32chars") is False
    assert is_production_safe_key("a_random_highly_secure_token_with_high_entropy_123456789") is True
