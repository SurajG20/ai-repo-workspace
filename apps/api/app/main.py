from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import router as auth_router
from .api.intelligence import router as intelligence_router
from .api.repositories import router as repositories_router
from .api.webhooks import router as webhooks_router
from .config import settings
from .core.database import engine
from .core.health import router as health_router
from .core.metrics import MetricsMiddleware, metrics_endpoint
from .core.ratelimit import MemoryRateLimiter, RateLimitMiddleware, RedisRateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    jobs_pool = await asyncpg.create_pool(
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        min_size=1,
        max_size=4,
        timeout=10.0,
    )
    app.state.jobs_pool = jobs_pool
    yield
    await jobs_pool.close()
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Repository Workspace API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.rate_limit_enabled:
        redis_url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        backend: MemoryRateLimiter | RedisRateLimiter
        if settings.rate_limit_use_redis:
            backend = RedisRateLimiter(redis_url)
        else:
            backend = MemoryRateLimiter()
        app.add_middleware(
            RateLimitMiddleware,
            backend=backend,
            limit=settings.rate_limit_requests_per_minute,
            window_seconds=60,
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(repositories_router)
    app.include_router(intelligence_router)
    app.include_router(webhooks_router)

    app.add_middleware(MetricsMiddleware)
    app.add_route("/metrics", metrics_endpoint, name="metrics", include_in_schema=False)

    return app


app = create_app()
