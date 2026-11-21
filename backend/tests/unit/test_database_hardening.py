"""Unit tests for database persistence hardening and production restrictions."""

import pytest
from app.core.config import Settings


def test_production_rejects_sqlite_dialect():
    """Verify that production environment strictly forbids SQLite dialect."""
    cfg = Settings(ENVIRONMENT="production", DB_DIALECT="sqlite")
    with pytest.raises(RuntimeError, match="PostgreSQL connection required in production mode"):
        _ = cfg.async_database_url

    with pytest.raises(RuntimeError, match="PostgreSQL connection required in production mode"):
        _ = cfg.sync_database_url


def test_production_rejects_sqlite_url(monkeypatch):
    """Verify that production rejects SQLite database URLs."""
    cfg = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        DATABASE_SYNC_URL="sqlite:///./test.db",
    )
    with pytest.raises(RuntimeError, match="SQLite is strictly prohibited"):
        _ = cfg.async_database_url

    with pytest.raises(RuntimeError, match="SQLite is strictly prohibited"):
        _ = cfg.sync_database_url


def test_production_accepts_postgres_url():
    """Verify that production generates valid PostgreSQL connection strings."""
    cfg = Settings(
        ENVIRONMENT="production",
        POSTGRES_SERVER="db.prod.internal",
        POSTGRES_PORT=5432,
        POSTGRES_USER="vantyx_prod",
        POSTGRES_PASSWORD="secure_password",
        POSTGRES_DB="vantyx_prod_db",
    )
    assert cfg.is_production is True
    assert "postgresql+asyncpg://vantyx_prod:secure_password@db.prod.internal:5432/vantyx_prod_db" in cfg.async_database_url
    assert "postgresql://vantyx_prod:secure_password@db.prod.internal:5432/vantyx_prod_db" in cfg.sync_database_url
