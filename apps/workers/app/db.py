from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg

from .config import settings


@asynccontextmanager
async def get_pool() -> AsyncIterator[asyncpg.Pool]:
    """Create a short-lived pool.

    Celery fork workers run each task with a fresh event loop
    (asyncio.run), and asyncpg pools are bound to the loop they were
    created on, so a cached module-level pool breaks across runs.
    """
    pool = await asyncpg.create_pool(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db,
        min_size=1,
        max_size=4,
        timeout=10.0,
    )
    try:
        yield pool
    finally:
        await pool.close()
