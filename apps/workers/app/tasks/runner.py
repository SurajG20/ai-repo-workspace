"""Generic executor for Indexing Pipeline Jobs.

The dispatcher claims a Job and sends its envelope here; this task runs the
stage implementation, then reports the outcome back to the pipeline, which
owns chaining, retries, and artifact cleanup. Celery/Redis only wakes
executors (ADR-0001): Postgres is the queue.
"""

from __future__ import annotations

import asyncio

import structlog
from jobs import ClaimedJob, IndexingPipeline, PostgresJobStore, Stage

from ..db import get_pool
from ..main import app
from .embedding import embed_stage
from .ingestion import clone_stage, snapshot_stage
from .parsing import parse_stage
from .sync_graph import graph_sync_stage

logger = structlog.get_logger(__name__)


async def _run_clone(claimed: ClaimedJob) -> dict:
    return await clone_stage(
        clone_url=claimed.repo.clone_url or claimed.meta.get("clone_url") or "",
        local_path=claimed.repo.local_path or claimed.meta.get("local_path") or "",
        # Token resolution from stored credentials lands with the api switch.
        access_token="",
    )


async def _run_snapshot(claimed: ClaimedJob) -> dict:
    return await snapshot_stage(
        local_path=claimed.repo.local_path or "",
        repository_id=str(claimed.repository_id),
    )


async def _run_parse(claimed: ClaimedJob) -> dict:
    return await parse_stage(
        repository_id=str(claimed.repository_id),
        snapshot_id=claimed.snapshot_id or "",
        repo_path=claimed.repo.local_path or claimed.meta.get("repo_path") or "",
        file_paths=claimed.meta.get("file_paths"),
    )


async def _run_graph_sync(claimed: ClaimedJob) -> dict:
    return await graph_sync_stage(
        repository_id=str(claimed.repository_id),
        language=claimed.repo.language or claimed.meta.get("language", ""),
        symbols=claimed.meta.get("symbols"),
        relationships=claimed.meta.get("relationships"),
        data_file=claimed.meta.get("data_file"),
    )


async def _run_embed(claimed: ClaimedJob) -> dict:
    return await embed_stage(
        repository_id=str(claimed.repository_id),
        language=claimed.repo.language or claimed.meta.get("language", ""),
        symbols=claimed.meta.get("symbols"),
        provider=claimed.meta.get("provider"),
        data_file=claimed.meta.get("data_file"),
    )


_STAGE_EXECUTORS = {
    Stage.CLONE: _run_clone,
    Stage.SNAPSHOT: _run_snapshot,
    Stage.PARSE: _run_parse,
    Stage.GRAPH_SYNC: _run_graph_sync,
    Stage.EMBED: _run_embed,
}


@app.task(name="run_claimed_job", bind=True, max_retries=0)
def run_claimed_job(self, envelope: dict) -> dict:
    asyncio.run(_execute(envelope))
    return {"status": "recorded"}


async def _execute(envelope: dict) -> None:
    claimed = ClaimedJob.from_payload(envelope)
    executor = _STAGE_EXECUTORS[claimed.stage]

    async with get_pool() as pool:
        pipeline = IndexingPipeline(PostgresJobStore(pool))
        try:
            result = await executor(claimed)
            children = await pipeline.complete(claimed, result)
            logger.info(
                "job_completed",
                job=str(claimed.job_id),
                stage=claimed.stage.value,
                chained=[child.id for child in children],
            )
        except Exception as e:
            logger.error(
                "job_failed",
                job=str(claimed.job_id),
                stage=claimed.stage.value,
                attempt=claimed.attempt + 1,
                error=str(e)[:2000],
            )
            await pipeline.fail(claimed, str(e)[:2000])
