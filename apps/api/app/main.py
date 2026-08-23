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

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(repositories_router)
    app.include_router(intelligence_router)
    app.include_router(webhooks_router)

    return app


app = create_app()
