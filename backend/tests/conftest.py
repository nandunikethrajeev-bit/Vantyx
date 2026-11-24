"""Pytest Fixtures for VANTYX Backend Tests with Database Isolation."""

import os
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Ensure an isolated test database is configured and initialized for the test session."""
    import asyncio
    import app.db.session as db_session
    from app.db.session import init_db, get_async_engine

    # 1. Point to dedicated isolated test database to protect persistent storage
    test_db_file = Path("data/test_vantyx.db").resolve()
    if test_db_file.exists():
        try:
            test_db_file.unlink()
        except Exception:
            pass

    test_db_url = f"sqlite+aiosqlite:///{test_db_file.as_posix()}"
    test_sync_url = f"sqlite:///{test_db_file.as_posix()}"
    settings.DATABASE_URL = test_db_url
    settings.DATABASE_SYNC_URL = test_sync_url

    # Reset cached engine singletons so they bind to the test database
    db_session._async_engine = None
    db_session._async_session_maker = None

    # 2. Initialize tables on clean test database
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())

    yield

    # 3. Graceful Windows-safe engine disposal and loop closure
    try:
        loop.run_until_complete(get_async_engine().dispose())
    except Exception:
        pass
    try:
        loop.close()
    except Exception:
        pass

    # Clean up test database file at end of session
    if test_db_file.exists():
        try:
            test_db_file.unlink()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def isolate_test_state_between_tests():
    """Ensure mutable scheduling and orchestration tables are isolated between tests."""
    yield
    from app.db.session import get_sync_engine
    from sqlalchemy import text
    try:
        with get_sync_engine().begin() as conn:
            conn.execute(text("DELETE FROM publish_schedules"))
            conn.execute(text("DELETE FROM daily_publishing_plans"))
            conn.execute(text("DELETE FROM workflow_steps"))
            conn.execute(text("DELETE FROM job_execution_logs"))
            conn.execute(text("DELETE FROM background_jobs"))
            conn.execute(text("DELETE FROM workflow_runs"))
    except Exception:
        pass


@pytest.fixture(scope="session")
def sync_client():
    """Synchronous test client for quick HTTP contract tests."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client():
    """Asynchronous httpx client for async endpoint testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def async_db_session():
    """Async database session fixture."""
    from app.db.session import get_async_session_maker
    maker = get_async_session_maker()
    async with maker() as session:
        yield session
