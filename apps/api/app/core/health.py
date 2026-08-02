from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from sqlalchemy import text

from ..config import settings
from ..core.database import engine

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


def _short_error(e: Exception) -> str:
    msg = str(e).split("\n")[0][:120]
    return f"{type(e).__name__}: {msg}"


async def _check_neo4j() -> str:
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_acquisition_timeout=3,
        )
        async with driver.session() as session:
            result = await session.run("RETURN 1")
            await result.single()
        await driver.close()
        return "ok"
    except Exception as e:
        return _short_error(e)


async def _check_qdrant() -> str:
    try:
        from qdrant_client import AsyncQdrantClient
        qdrant = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key or None,
            timeout=3.0,
            check_compatibility=False,
        )
        await qdrant.get_collections()
        await qdrant.close()
        return "ok"
    except Exception as e:
        return _short_error(e)


@router.get("/health")
async def health_check() -> dict[str, Any]:
    import asyncio
    neo4j_status, qdrant_status = await asyncio.gather(
        _check_neo4j(), _check_qdrant()
    )
    deps = {"neo4j": neo4j_status, "qdrant": qdrant_status}
    all_ok = all(v == "ok" for v in deps.values())
    logger.info("health_check", deps=deps)
    return {
        "status": "ok" if all_ok else "degraded",
        "version": "0.1.0",
        "dependencies": deps,
    }


@router.get("/health/ready")
async def readiness_check() -> dict[str, Any]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db = "ok"
    except Exception as e:
        db = _short_error(e)
    return {"status": "ready" if db == "ok" else "degraded", "database": db}
