"""Bridge between the Indexing Pipeline and Celery execution.

The pipeline (packages/jobs) owns the DAG, status transitions, claiming,
retries, and artifacts. This beat task only wakes execution: it claims due
Jobs and sends their envelopes to run_claimed_job. Postgres is the queue
(ADR-0001); there is no AsyncResult polling.
"""

from __future__ import annotations

import asyncio
import os
import socket
from datetime import timedelta

import structlog

from jobs import IndexingPipeline, PostgresJobStore

from ..db import get_pool
from ..main import app
logger = structlog.get_logger(__name__)

STALE_AFTER = timedelta(minutes=15)
DISPATCH_BATCH = 10


@app.task(name="dispatch_pending_jobs", bind=True, max_retries=1)
def dispatch_pending_jobs(self) -> dict:
    return asyncio.run(_run_dispatcher())


async def _run_dispatcher() -> dict:
    async with get_pool() as pool:
        pipeline = IndexingPipeline(PostgresJobStore(pool))
        worker_id = f"dispatcher-{socket.gethostname()}-{os.getpid()}"
        dispatched = 0

        for _ in range(DISPATCH_BATCH):
            claimed = await pipeline.claim_next(worker_id, stale_after=STALE_AFTER)
            if claimed is None:
                break
            app.send_task("run_claimed_job", kwargs={"envelope": claimed.to_payload()})
            dispatched += 1
            logger.info(
                "job_dispatched",
                job=str(claimed.job_id),
                stage=claimed.stage.value,
                attempt=claimed.attempt + 1,
            )

        return {"dispatched": dispatched}
