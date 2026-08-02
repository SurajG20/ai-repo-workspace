from __future__ import annotations

"""Bridge between database indexing jobs and celery task execution.

The API enqueues IndexingJob rows; this dispatcher picks them up,
runs the matching celery task, records results, and chains the next
pipeline stage (parse -> graph sync + embed)."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import structlog

from ..db import get_pool
from ..main import app

logger = structlog.get_logger(__name__)

JOB_TASK_MAP: dict[str, str] = {
    "clone": "clone_repository",
    "snapshot": "create_snapshot",
    "parse": "parse_repository",
    "graph_sync": "sync_to_neo4j",
    "embed": "embed_repository",
}

TERMINAL_JOB_TYPES = {"graph_sync", "embed"}

_QUEUED_SQL = """
    SELECT id, repository_id, job_type, metadata, status, snapshot_id
    FROM indexing_jobs
    WHERE status = 'queued'
      AND retry_count < max_retries
    ORDER BY created_at
    LIMIT 10
"""

_RUNNING_SQL = """
    SELECT id, job_type, celery_task_id, metadata, repository_id, snapshot_id
    FROM indexing_jobs
    WHERE status IN ('running', 'started', 'retry')
      AND celery_task_id IS NOT NULL
"""

_REPO_SQL = """
    SELECT id, full_name, local_path, clone_url, status, language
    FROM repositories
    WHERE id = $1 AND deleted_at IS NULL
"""


async def _run_dispatcher() -> None:
    async with get_pool() as pool:
        async with pool.acquire() as conn:
            running = await conn.fetch(_RUNNING_SQL)
            for row in running:
                await _finalize_running(conn, row)

            queued = await conn.fetch(_QUEUED_SQL)
            for row in queued:
                await _dispatch_job(conn, row)


async def _finalize_running(conn: asyncpg.Connection, row: asyncpg.Record) -> None:
    from celery.result import AsyncResult

    job_id = row["id"]
    task_id = row["celery_task_id"]
    result = AsyncResult(task_id)

    if result.state == "PENDING":
        return

    if result.state == "SUCCESS":
        payload = result.result or {}
        await conn.execute(
            """
            UPDATE indexing_jobs
            SET status = 'completed', completed_at = $2, progress = 1.0,
                metadata = $3
            WHERE id = $1
            """,
            job_id,
            datetime.now(timezone.utc),
            json.dumps(payload, default=str),
        )
        logger.info("job_completed", job=str(job_id), task=row["job_type"])
        await _chain_next_stage(conn, row, payload)
        return

    if result.state in ("FAILURE", "REVOKED"):
        error = str(result.result or result.state)[:2000]
        await conn.execute(
            """
            UPDATE indexing_jobs
            SET status = 'failed', error_message = $2, completed_at = $3
            WHERE id = $1
            """,
            job_id,
            error,
            datetime.now(timezone.utc),
        )
        logger.error("job_failed", job=str(job_id), task=row["job_type"], error=error)
        return

    if result.state == "RETRY":
        return


async def _dispatch_job(conn: asyncpg.Connection, row: asyncpg.Record) -> None:
    job_id = row["id"]
    job_type = row["job_type"]
    task_name = JOB_TASK_MAP.get(job_type)
    if not task_name:
        await conn.execute(
            "UPDATE indexing_jobs SET status = 'failed', error_message = $2 WHERE id = $1",
            job_id,
            f"no task registered for job_type={job_type}",
        )
        return

    repo = await conn.fetchrow(_REPO_SQL, row["repository_id"])
    if not repo:
        await conn.execute(
            "UPDATE indexing_jobs SET status = 'failed', error_message = $2 WHERE id = $1",
            job_id,
            "repository not found or deleted",
        )
        return

    meta = row["metadata"]
    if isinstance(meta, str):
        meta = json.loads(meta or "{}")
    kwargs: dict[str, Any] = {}
    if job_type == "clone":
        kwargs = {
            "clone_url": repo["clone_url"] or meta.get("clone_url"),
            "local_path": repo["local_path"] or meta.get("local_path"),
            "access_token": meta.get("access_token", ""),
        }
        await conn.execute(
            "UPDATE repositories SET status = 'cloning' WHERE id = $1", repo["id"]
        )
    elif job_type == "snapshot":
        kwargs = {"local_path": repo["local_path"], "repository_id": str(repo["id"])}
    elif job_type == "parse":
        snapshot_id = row["snapshot_id"] or meta.get("snapshot_id")
        kwargs = {
            "repository_id": str(repo["id"]),
            "snapshot_id": str(snapshot_id) if snapshot_id else "",
            "repo_path": repo["local_path"],
            "file_paths": meta.get("file_paths"),
        }
        await conn.execute(
            "UPDATE repositories SET status = 'indexing' WHERE id = $1", repo["id"]
        )
    elif job_type == "graph_sync":
        kwargs = {
            "repository_id": str(repo["id"]),
            "language": repo["language"] or meta.get("language", ""),
            "symbols": meta.get("symbols"),
            "relationships": meta.get("relationships"),
            "data_file": meta.get("data_file"),
        }
    elif job_type == "embed":
        kwargs = {
            "repository_id": str(repo["id"]),
            "language": repo["language"] or meta.get("language", ""),
            "symbols": meta.get("symbols"),
            "provider": meta.get("provider"),
            "data_file": meta.get("data_file"),
        }

    async with conn.transaction():
        celery_task = app.send_task(task_name, kwargs=kwargs)
        await conn.execute(
            """
            UPDATE indexing_jobs
            SET status = 'running', celery_task_id = $2, started_at = $3
            WHERE id = $1
            """,
            job_id,
            celery_task.id,
            datetime.now(timezone.utc),
        )
    logger.info("job_dispatched", job=str(job_id), task=task_name, celery=str(celery_task.id))


async def _chain_next_stage(
    conn: asyncpg.Connection,
    row: asyncpg.Record,
    payload: dict[str, Any],
) -> None:
    job_id = row["id"]
    job_type = row["job_type"]
    repo_id = row["repository_id"]
    snapshot_id = row["snapshot_id"]

    async def _create_job(job_type: str, meta: dict | None = None) -> None:
        await conn.execute(
            """
            INSERT INTO indexing_jobs (id, repository_id, snapshot_id, job_type,
                                       status, metadata, created_at, updated_at)
            VALUES (gen_random_uuid(), $1, $2, $3, 'queued', $4, now(), now())
            """,
            repo_id,
            snapshot_id,
            job_type,
            json.dumps(meta or {}),
        )

    if job_type in ("snapshot", "clone"):
        if job_type == "snapshot":
            sha = payload.get("commit_sha") or payload.get("sha") or "unknown"
            await conn.execute(
                """
                INSERT INTO repository_snapshots
                    (id, repository_id, commit_sha, branch, file_count,
                     total_size_bytes, indexed, created_at)
                VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, false, now())
                ON CONFLICT DO NOTHING
                """,
                repo_id,
                sha,
                payload.get("branch", "main"),
                int(payload.get("file_count", 0)),
                int(payload.get("total_size_bytes", 0)),
            )
            snapshot_row = await conn.fetchrow(
                "SELECT id FROM repository_snapshots WHERE repository_id = $1 ORDER BY created_at DESC LIMIT 1",
                repo_id,
            )
            new_snapshot_id = snapshot_row["id"] if snapshot_row else None
            await conn.execute(
                "UPDATE repositories SET status = 'active', last_synced_sha = $2 WHERE id = $1",
                repo_id,
                sha,
            )
            await _create_job(
                "parse",
                {"repo_path": (await conn.fetchrow(_REPO_SQL, repo_id))["local_path"]},
            )
            if new_snapshot_id:
                await conn.execute(
                    "UPDATE indexing_jobs SET snapshot_id = $2 WHERE id = $1",
                    job_id,
                    new_snapshot_id,
                )
        else:
            sha = payload.get("sha")
            await conn.execute(
                """
                UPDATE repositories
                SET status = 'active', last_synced_sha = $2, last_synced_at = $3
                WHERE id = $1
                """,
                repo_id,
                sha,
                datetime.now(timezone.utc),
            )
            await _create_job("parse", {"repo_path": payload.get("path")})

    elif job_type == "parse":
        symbols = payload.get("symbols", [])
        relationships = payload.get("relationships", [])
        language = payload.get("language") or ""

        meta: dict[str, Any] = {}
        if payload.get("data_file"):
            meta["data_file"] = payload["data_file"]
        else:
            meta["symbols"] = symbols
            meta["relationships"] = relationships

        await _create_job("graph_sync", {**meta, "language": language})
        await _create_job("embed", {**meta, "language": language, "provider": None})


@app.task(name="dispatch_pending_jobs", bind=True, max_retries=1)
def dispatch_pending_jobs(self) -> dict:
    return asyncio.run(_run_dispatcher())
