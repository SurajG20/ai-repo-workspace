from __future__ import annotations

import structlog

from .main import app

logger = structlog.get_logger(__name__)


@app.task(name="health_check")
def health_check() -> dict[str, str]:
    logger.info("worker_health_check")
    return {"status": "ok"}
