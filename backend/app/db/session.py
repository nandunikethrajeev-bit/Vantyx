"""VANTYX Database Session & Connection Management.

Configures SQLAlchemy 2.x async engine, session makers, table initialization,
and connection checks. Supports PostgreSQL and resilient local SQLite.
"""

import asyncio
from typing import AsyncGenerator, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.logging import logger
from app.db.base import Base

# Lazy-initialised async engine
_async_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Retrieve or create the global async database engine."""
    global _async_engine
    if _async_engine is None:
        url = settings.async_database_url
        is_sqlite = url.startswith("sqlite")

        if is_sqlite:
            _async_engine = create_async_engine(
                url,
                echo=settings.DEBUG,
                connect_args={"check_same_thread": False},
            )
        else:
            _async_engine = create_async_engine(
                url,
                echo=settings.DEBUG,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_pre_ping=True,
                connect_args={"timeout": 2.0},
            )
    return _async_engine


def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    """Retrieve or create the global async session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding database sessions."""
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create database tables if they do not exist."""
    engine = get_async_engine()
    # Import all models to ensure they are registered with Base.metadata
    import app.db.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Resilient schema patch for audio_metrics column
        try:
            if "sqlite" in settings.async_database_url:
                res = await conn.execute(text("PRAGMA table_info(video_scenes)"))
                cols = [r[1] for r in res.fetchall()]
                if "audio_metrics" not in cols:
                    await conn.execute(text("ALTER TABLE video_scenes ADD COLUMN audio_metrics JSON"))
            else:
                await conn.execute(text("ALTER TABLE video_scenes ADD COLUMN IF NOT EXISTS audio_metrics JSON"))
        except Exception as exc:
            logger.debug(f"audio_metrics column verification note: {exc}")

        # Resilient schema patch for creator OAuth & channel authorization columns
        creator_cols_sqlite = [
            ("oauth_status", "VARCHAR(32) DEFAULT 'disconnected'"),
            ("google_account_id", "VARCHAR(128)"),
            ("google_account_email", "VARCHAR(255)"),
            ("verified_channel_id", "VARCHAR(128)"),
            ("verified_channel_title", "VARCHAR(255)"),
            ("verified_at", "TIMESTAMP"),
            ("access_token", "TEXT"),
            ("refresh_token", "TEXT"),
            ("token_expires_at", "TIMESTAMP"),
            ("oauth_scopes", "VARCHAR(512)"),
            ("is_revoked", "BOOLEAN DEFAULT 0"),
            ("revoked_at", "TIMESTAMP"),
            ("revocation_reason", "VARCHAR(512)"),
        ]
        creator_cols_pg = [
            ("oauth_status", "VARCHAR(32) DEFAULT 'disconnected'"),
            ("google_account_id", "VARCHAR(128)"),
            ("google_account_email", "VARCHAR(255)"),
            ("verified_channel_id", "VARCHAR(128)"),
            ("verified_channel_title", "VARCHAR(255)"),
            ("verified_at", "TIMESTAMP WITH TIME ZONE"),
            ("access_token", "TEXT"),
            ("refresh_token", "TEXT"),
            ("token_expires_at", "TIMESTAMP WITH TIME ZONE"),
            ("oauth_scopes", "VARCHAR(512)"),
            ("is_revoked", "BOOLEAN DEFAULT FALSE"),
            ("revoked_at", "TIMESTAMP WITH TIME ZONE"),
            ("revocation_reason", "VARCHAR(512)"),
        ]
        try:
            if "sqlite" in settings.async_database_url:
                res = await conn.execute(text("PRAGMA table_info(creators)"))
                existing = [r[1] for r in res.fetchall()]
                for col_name, col_def in creator_cols_sqlite:
                    if col_name not in existing:
                        await conn.execute(text(f"ALTER TABLE creators ADD COLUMN {col_name} {col_def}"))
            else:
                for col_name, col_def in creator_cols_pg:
                    await conn.execute(text(f"ALTER TABLE creators ADD COLUMN IF NOT EXISTS {col_name} {col_def}"))
        except Exception as exc:
            logger.debug(f"creator OAuth columns migration note: {exc}")
    logger.info("Database schema verified and active")


async def _probe_db(engine: AsyncEngine) -> str:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        result.scalar()
        is_sqlite = "sqlite" in settings.async_database_url
        if is_sqlite:
            return "Local SQLite persistent engine active and responsive"
        return "PostgreSQL connection active and responsive"


async def check_db_connectivity(timeout_seconds: float = 2.0) -> Tuple[bool, str]:
    """Execute a lightweight connectivity probe against the database.
    
    Returns:
        Tuple of (is_connected, status_detail_message)
    """
    engine = get_async_engine()
    try:
        msg = await asyncio.wait_for(_probe_db(engine), timeout=timeout_seconds)
        return True, msg
    except (asyncio.TimeoutError, TimeoutError):
        error_msg = f"Database connection timed out after {timeout_seconds}s"
        logger.warning(f"Database health check failed: {error_msg}")
        return False, error_msg
    except Exception as exc:
        error_msg = f"Database unreachable: {type(exc).__name__}"
        logger.warning(f"Database health check failed: {error_msg}")
        return False, error_msg


def get_sync_engine():
    """Create a synchronous engine for Alembic and migration operations."""
    url = settings.sync_database_url
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(
        url,
        echo=settings.DEBUG,
        pool_pre_ping=True,
    )
