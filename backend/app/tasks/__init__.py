"""VANTYX Asynchronous Task Package.

Defines registered Celery background tasks for autonomous pipeline execution,
video rendering, scheduled distribution, and analytics intelligence collection.
"""

import asyncio
from typing import Any, Callable, Coroutine
from app.db.session import get_async_session_maker


async def _execute_with_db(coro_fn: Callable[[Any], Coroutine[Any, Any, Any]]) -> Any:
    session_maker = get_async_session_maker()
    async with session_maker() as session:
        try:
            result = await coro_fn(session)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise


def run_task_async(coro_fn: Callable[[Any], Coroutine[Any, Any, Any]]) -> Any:
    """Execute an async database coroutine synchronously inside a Celery task worker."""
    return asyncio.run(_execute_with_db(coro_fn))
