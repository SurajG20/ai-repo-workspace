from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg

from .models import ClaimedJob, Job, RepoContext, Stage
from .store import JobStore, RepositoryDeletedError

logger = logging.getLogger("jobs.postgres")

_REPO_STATUS_ON_CLAIM: dict[Stage, str | None] = {
    Stage.CLONE: "cloning",
    Stage.SNAPSHOT: None,
    Stage.PARSE: "indexing",
    Stage.GRAPH_SYNC: "indexing",
    Stage.EMBED: "indexing",
}

_RECLAIM_SQL = """
WITH reclaimed AS (
    UPDATE indexing_jobs
       SET retry_count = retry_count + 1,
           status = CASE WHEN retry_count + 1 >= max_retries THEN 'failed' ELSE 'queued' END,
           error_message = CASE
               WHEN retry_count + 1 >= max_retries
                   THEN COALESCE(error_message || ' | ', '') || 'stale lock reclaimed'
               ELSE error_message END,
           completed_at = CASE WHEN retry_count + 1 >= max_retries THEN now() ELSE NULL END,
           locked_by = NULL,
           locked_at = NULL
     WHERE status IN ('running', 'started', 'retry')
       AND (COALESCE(locked_at, started_at) IS NULL OR COALESCE(locked_at, started_at) < $1)
    RETURNING repository_id, status)
UPDATE repositories r
   SET status = 'error'
  FROM reclaimed
 WHERE r.id = reclaimed.repository_id
   AND reclaimed.status = 'failed'
"""

_CANCEL_DELETED_SQL = """
UPDATE indexing_jobs j
   SET status = 'cancelled', completed_at = now()
  FROM repositories r
 WHERE r.id = j.repository_id
   AND r.deleted_at IS NOT NULL
   AND j.status = 'queued'
"""

_CLAIM_SQL = """
WITH picked AS (
    SELECT j.id
      FROM indexing_jobs j
      JOIN repositories r ON r.id = j.repository_id AND r.deleted_at IS NULL
     WHERE j.status = 'queued'
       AND j.retry_count < j.max_retries
     ORDER BY j.created_at
     LIMIT 1
     FOR UPDATE OF j SKIP LOCKED
), claimed AS (
    UPDATE indexing_jobs j
       SET status = 'running',
           locked_by = $1,
           locked_at = now(),
           started_at = COALESCE(j.started_at, now())
      FROM picked
     WHERE j.id = picked.id
    RETURNING j.id, j.repository_id, j.snapshot_id, j.parent_job_id,
              j.job_type, j.metadata, j.retry_count
)
SELECT c.id, c.repository_id, c.snapshot_id, c.parent_job_id,
       c.job_type, c.metadata, c.retry_count,
       r.full_name, r.local_path, r.clone_url, r.language, r.owner_id
  FROM claimed c
  JOIN repositories r ON r.id = c.repository_id
"""


def _as_dict(metadata: Any) -> dict[str, Any]:
    if isinstance(metadata, str):
        return json.loads(metadata or "{}")
    return dict(metadata or {})


def _uuid(value: str | None) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None


class PostgresJobStore(JobStore):
    """Postgres adapter: the authoritative queue (ADR-0001)."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def enqueue(
        self,
        repository_id: str,
        stage: Stage,
        *,
        snapshot_id: str | None = None,
        parent_job_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        async with self._pool.acquire() as conn, conn.transaction():
            alive = await conn.fetchval(
                """
                    SELECT true FROM repositories
                     WHERE id = $1 AND deleted_at IS NULL
                       FOR SHARE
                    """,
                _uuid(repository_id),
            )
            if not alive:
                raise RepositoryDeletedError(repository_id)
            row = await conn.fetchrow(
                """
                    INSERT INTO indexing_jobs
                        (repository_id, snapshot_id, job_type, status, metadata, parent_job_id)
                    VALUES ($1::uuid, $2::uuid, $3, 'queued', $4::jsonb, $5::uuid)
                    RETURNING id
                    """,
                _uuid(repository_id),
                _uuid(snapshot_id),
                stage.value,
                json.dumps(metadata or {}, default=str),
                _uuid(parent_job_id),
            )
        return Job(
            id=str(row["id"]),
            repository_id=repository_id,
            stage=stage,
            status="queued",
            snapshot_id=snapshot_id,
            parent_job_id=parent_job_id,
            metadata=dict(metadata or {}),
        )

    async def claim_next(self, worker_id: str, stale_after: timedelta) -> ClaimedJob | None:
        horizon = datetime.now(UTC) - stale_after
        async with self._pool.acquire() as conn, conn.transaction():
            await conn.execute(_RECLAIM_SQL, horizon)
            await conn.execute(_CANCEL_DELETED_SQL)
            row = await conn.fetchrow(_CLAIM_SQL, worker_id)
            if row is None:
                return None
            stage = Stage(row["job_type"])
            repo_status = _REPO_STATUS_ON_CLAIM.get(stage)
            if repo_status is not None:
                await conn.execute(
                    "UPDATE repositories SET status = $2 WHERE id = $1",
                    row["repository_id"],
                    repo_status,
                )

        return ClaimedJob(
            job_id=str(row["id"]),
            repository_id=str(row["repository_id"]),
            stage=stage,
            attempt=row["retry_count"],
            snapshot_id=str(row["snapshot_id"]) if row["snapshot_id"] else None,
            parent_job_id=str(row["parent_job_id"]) if row["parent_job_id"] else None,
            repo=RepoContext(
                id=str(row["repository_id"]),
                full_name=row["full_name"],
                local_path=row["local_path"],
                clone_url=row["clone_url"],
                language=row["language"],
                owner_id=str(row["owner_id"]) if row["owner_id"] else None,
            ),
            meta=_as_dict(row["metadata"]),
        )

    async def complete(self, job_id: str, result: dict[str, Any]) -> None:
        await self._pool.execute(
            """
            UPDATE indexing_jobs
               SET status = 'completed',
                   progress = 1.0,
                   completed_at = now(),
                   metadata = $2::jsonb
             WHERE id = $1
            """,
            _uuid(job_id),
            json.dumps(result, default=str),
        )

    async def fail(self, job_id: str) -> str:
        async with self._pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                """
                UPDATE indexing_jobs
                   SET retry_count = retry_count + 1,
                       status = CASE
                           WHEN retry_count + 1 >= max_retries THEN 'failed'
                           ELSE 'queued' END,
                       error_message = $2,
                       completed_at = CASE
                           WHEN retry_count + 1 >= max_retries THEN now()
                           ELSE NULL END,
                       locked_by = NULL,
                       locked_at = NULL
                 WHERE id = $1
                RETURNING repository_id, status
                """,
                _uuid(job_id),
            )
            if row["status"] == "failed":
                await conn.execute(
                    "UPDATE repositories SET status = 'error' WHERE id = $1",
                    row["repository_id"],
                )
        return row["status"]

    async def link_snapshot(self, job_id: str, snapshot_id: str) -> None:
        await self._pool.execute(
            "UPDATE indexing_jobs SET snapshot_id = $2::uuid WHERE id = $1::uuid",
            _uuid(job_id),
            _uuid(snapshot_id),
        )

    async def insert_snapshot(
        self,
        repository_id: str,
        commit_sha: str,
        branch: str,
        file_count: int,
        total_size_bytes: int,
    ) -> str:
        snapshot_id = await self._pool.fetchval(
            """
            INSERT INTO repository_snapshots
                (repository_id, commit_sha, branch, file_count, total_size_bytes, indexed)
            VALUES ($1::uuid, $2, $3, $4, $5, false)
            RETURNING id
            """,
            _uuid(repository_id),
            commit_sha,
            branch,
            file_count,
            total_size_bytes,
        )
        return str(snapshot_id)

    async def set_repo_active(
        self, repository_id: str, sha: str | None, *, touch_synced_at: bool
    ) -> None:
        await self._pool.execute(
            """
            UPDATE repositories
               SET status = 'active',
                   last_synced_sha = COALESCE($2, last_synced_sha),
                   last_synced_at = CASE WHEN $3 THEN now() ELSE last_synced_at END
             WHERE id = $1
            """,
            _uuid(repository_id),
            sha,
            touch_synced_at,
        )

    async def siblings_completed(self, parent_job_id: str, exclude_job_id: str) -> bool:
        done = await self._pool.fetchval(
            """
            SELECT COALESCE(bool_and(status = 'completed'), true)
              FROM indexing_jobs
             WHERE parent_job_id = $1::uuid
               AND id <> $2::uuid
            """,
            _uuid(parent_job_id),
            _uuid(exclude_job_id),
        )
        return bool(done)
