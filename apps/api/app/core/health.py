from __future__ import annotations

import structlog
from fastapi import APIRouter

from ..config import settings

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("/health")
async def health_check() -> dict[str, str]:
    logger.info("health_check")
    return {"status": "ok", "version": "0.1.0"}


@router.get("/health/ready")
async def readiness_check() -> dict[str, str]:
    return {"status": "ready"}
