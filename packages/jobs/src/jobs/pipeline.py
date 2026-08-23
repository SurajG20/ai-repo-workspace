from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Any

from .dag import NEXT_STAGES, TERMINAL_STAGES
from .models import ClaimedJob, Job, Stage
from .store import JobStore

logger = logging.getLogger("jobs.pipeline")

DEFAULT_STALE_AFTER = timedelta(minutes=15)


class IndexingPipeline:
    """The Indexing Pipeline: one module owning the job DAG, transitions,
    claiming, retries, and artifact lifecycle.

    Interface: enqueue / claim_next / complete / fail. Everything else is
    implementation.
    """

    def __init__(self, store: JobStore) -> None:
        self._store = store

    async def enqueue(
        self,
        repository_id: str,
        stage: Stage,
        *,
        snapshot_id: str | None = None,
        parent_job_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        return await self._store.enqueue(
            repository_id,
            stage,
            snapshot_id=snapshot_id,
            parent_job_id=parent_job_id,
            metadata=metadata,
        )

    async def claim_next(
        self, worker_id: str, stale_after: timedelta = DEFAULT_STALE_AFTER
    ) -> ClaimedJob | None:
        return await self._store.claim_next(worker_id, stale_after)

    async def complete(self, claimed: ClaimedJob, result: dict[str, Any]) -> list[Job]:
        """Record success and chain the next stages per the static DAG.

        Returns the newly enqueued child Jobs (empty for terminal stages).
        """
        await self._store.complete(claimed.job_id, result)
        logger.info(
            "job completed job=%s stage=%s", claimed.job_id, claimed.stage.value
        )

        if claimed.stage in TERMINAL_STAGES:
            await self._cleanup_artifact(claimed)
            return []

        if claimed.stage in TERMINAL_STAGES:
            self._cleanup_artifact(claimed)
            return []

        children: list[Job] = []
        for stage in NEXT_STAGES[claimed.stage]:
            children.append(await self._chain(claimed, stage, result))
        return children

    async def fail(self, claimed: ClaimedJob, error: str) -> str:
        outcome = await self._store.fail(claimed.job_id)
        logger.warning(
            "job failed job=%s stage=%s attempt=%s outcome=%s error=%s",
            claimed.job_id,
            claimed.stage.value,
            claimed.attempt + 1,
            outcome,
            error[:500],
        )
        return outcome

    # -- chaining rules -------------------------------------------------

    async def _chain(self, claimed: ClaimedJob, stage: Stage, result: dict[str, Any]) -> Job:
        if stage is Stage.PARSE:
            return await self._chain_parse(claimed, result)
        if stage is Stage.GRAPH_SYNC:
            return await self._chain_parse_consumer(
                claimed, Stage.GRAPH_SYNC, result, extra={}
            )
        if stage is Stage.EMBED:
            return await self._chain_parse_consumer(
                claimed, Stage.EMBED, result, extra={"provider": None}
            )
        raise ValueError(f"no chaining rule from {claimed.stage.value} to {stage.value}")

    async def _chain_parse(self, claimed: ClaimedJob, result: dict[str, Any]) -> Job:
        snapshot_id = claimed.snapshot_id
        metadata: dict[str, Any] = {}

        if claimed.stage is Stage.SNAPSHOT:
            sha = result.get("commit_sha") or result.get("sha") or "unknown"
            snapshot_id = await self._store.insert_snapshot(
                claimed.repository_id,
                sha,
                result.get("branch", "main"),
                int(result.get("file_count", 0)),
                int(result.get("total_size_bytes", 0)),
            )
            await self._store.link_snapshot(claimed.job_id, snapshot_id)
            await self._store.set_repo_active(
                claimed.repository_id, sha, touch_synced_at=False
            )
            metadata["repo_path"] = claimed.repo.local_path or ""
        else:  # clone
            sha = result.get("sha")
            await self._store.set_repo_active(
                claimed.repository_id, sha, touch_synced_at=True
            )
            metadata["repo_path"] = result.get("path") or claimed.repo.local_path or ""

        return await self._store.enqueue(
            claimed.repository_id,
            Stage.PARSE,
            snapshot_id=snapshot_id,
            parent_job_id=claimed.job_id,
            metadata=metadata,
        )

    async def _chain_parse_consumer(
        self, claimed: ClaimedJob, stage: Stage, result: dict[str, Any], *, extra: dict[str, Any]
    ) -> Job:
        metadata: dict[str, Any] = {
            "language": result.get("language") or "",
        }
        data_file = result.get("data_file")
        if data_file:
            # One Artifact on disk; consumers reference it and the pipeline
            # deletes it once every consumer has finished.
            metadata["data_file"] = data_file
        else:
            metadata["symbols"] = result.get("symbols", [])
            metadata["relationships"] = result.get("relationships", [])
        metadata.update(extra)

        return await self._store.enqueue(
            claimed.repository_id,
            stage,
            snapshot_id=claimed.snapshot_id,
            parent_job_id=claimed.job_id,
            metadata=metadata,
        )

    # -- artifacts -------------------------------------------------------

    async def _cleanup_artifact(self, claimed: ClaimedJob) -> None:
        """Delete a parse Artifact once every consumer has finished with it.

        A failed consumer leaves the Artifact in place: retries need it,
        and an operator may want to inspect it.
        """
        data_file = claimed.meta.get("data_file")
        if not data_file or not claimed.parent_job_id:
            return
        if await self._store.siblings_completed(claimed.parent_job_id, claimed.job_id):
            try:
                os.unlink(data_file)
                logger.info("artifact deleted path=%s", data_file)
            except OSError:
                pass
