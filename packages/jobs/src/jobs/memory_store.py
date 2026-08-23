from __future__ import annotations

import copy
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .models import ClaimedJob, Job, RepoContext, Stage
from .store import JobStore, RepositoryDeletedError

_REPO_STATUS_ON_CLAIM: dict[Stage, str | None] = {
    Stage.CLONE: "cloning",
    Stage.SNAPSHOT: None,
    Stage.PARSE: "indexing",
    Stage.GRAPH_SYNC: "indexing",
    Stage.EMBED: "indexing",
}


@dataclass
class _Repo:
    id: str
    full_name: str
    local_path: str | None
    clone_url: str | None
    language: str | None
    owner_id: str | None = None
    status: str = "pending"
    deleted_at: datetime | None = None
    last_synced_sha: str | None = None


@dataclass
class _JobRow:
    id: str
    repository_id: str
    stage: Stage
    status: str = "queued"
    snapshot_id: str | None = None
    parent_job_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    locked_by: str | None = None
    locked_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    progress: float = 0.0


@dataclass
class _Snapshot:
    id: str
    repository_id: str
    commit_sha: str
    branch: str
    file_count: int
    total_size_bytes: int


def _utcnow() -> datetime:
    return datetime.now(UTC)


class MemoryJobStore(JobStore):
    """In-memory adapter for the pipeline seam: same semantics, no Postgres."""

    def __init__(self, now_fn: Callable[[], datetime] = _utcnow) -> None:
        self._now = now_fn
        self._repos: dict[str, _Repo] = {}
        self._jobs: dict[str, _JobRow] = {}
        self._snapshots: list[_Snapshot] = []
        self._seq = 0

    # -- test fixtures -------------------------------------------------

    def add_repository(
        self,
        repository_id: str | None = None,
        *,
        full_name: str = "owner/name",
        local_path: str | None = "/repos/x",
        clone_url: str | None = "https://github.com/owner/name",
        language: str | None = "python",
        owner_id: str | None = None,
        status: str = "active",
        deleted: bool = False,
    ) -> str:
        rid = repository_id or str(uuid.uuid4())
        self._repos[rid] = _Repo(
            id=rid,
            full_name=full_name,
            local_path=local_path,
            clone_url=clone_url,
            language=language,
            owner_id=owner_id,
            status=status,
            deleted_at=self._now() if deleted else None,
        )
        return rid

    def get_job(self, job_id: str) -> Job:
        row = self._jobs[job_id]
        return Job(
            id=row.id,
            repository_id=row.repository_id,
            stage=row.stage,
            status=row.status,
            snapshot_id=row.snapshot_id,
            parent_job_id=row.parent_job_id,
            metadata=copy.deepcopy(row.metadata),
        )

    def job_field(self, job_id: str, name: str) -> Any:
        return getattr(self._jobs[job_id], name)

    def repo_status(self, repository_id: str) -> str:
        return self._repos[repository_id].status

    def snapshot_count(self) -> int:
        return len(self._snapshots)

    # -- JobStore ------------------------------------------------------

    async def enqueue(
        self,
        repository_id: str,
        stage: Stage,
        *,
        snapshot_id: str | None = None,
        parent_job_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        repo = self._repos.get(repository_id)
        if repo is None or repo.deleted_at is not None:
            raise RepositoryDeletedError(repository_id)
        self._seq += 1
        row = _JobRow(
            id=str(uuid.uuid4()),
            repository_id=repository_id,
            stage=stage,
            snapshot_id=snapshot_id,
            parent_job_id=parent_job_id,
            metadata=dict(metadata or {}),
            created_at=self._now() + timedelta(microseconds=self._seq),
        )
        self._jobs[row.id] = row
        return Job(
            id=row.id,
            repository_id=row.repository_id,
            stage=row.stage,
            status=row.status,
            snapshot_id=row.snapshot_id,
            parent_job_id=row.parent_job_id,
            metadata=copy.deepcopy(row.metadata),
        )

    async def claim_next(self, worker_id: str, stale_after: timedelta) -> ClaimedJob | None:
        now = self._now()
        horizon = now - stale_after

        for row in list(self._jobs.values()):
            if row.status not in ("running", "started", "retry"):
                continue
            marker = row.locked_at or row.started_at
            if marker is not None and marker >= horizon:
                continue
            row.retry_count += 1
            row.locked_by = None
            row.locked_at = None
            if row.retry_count >= row.max_retries:
                row.status = "failed"
                row.completed_at = now
                row.error_message = (
                    (row.error_message + " | " if row.error_message else "")
                    + "stale lock reclaimed"
                )
                repo = self._repos.get(row.repository_id)
                if repo is not None:
                    repo.status = "error"
            else:
                row.status = "queued"

        for row in self._jobs.values():
            if row.status != "queued":
                continue
            repo = self._repos.get(row.repository_id)
            if repo is not None and repo.deleted_at is not None:
                row.status = "cancelled"
                row.completed_at = now

        eligible = [
            row
            for row in self._jobs.values()
            if row.status == "queued"
            and row.retry_count < row.max_retries
            and not self._repos[row.repository_id].deleted_at
        ]
        if not eligible:
            return None
        row = min(eligible, key=lambda r: r.created_at)

        row.status = "running"
        row.locked_by = worker_id
        row.locked_at = now
        if row.started_at is None:
            row.started_at = now

        new_repo_status = _REPO_STATUS_ON_CLAIM[row.stage]
        repo = self._repos[row.repository_id]
        if new_repo_status is not None:
            repo.status = new_repo_status

        return ClaimedJob(
            job_id=row.id,
            repository_id=row.repository_id,
            stage=row.stage,
            attempt=row.retry_count,
            snapshot_id=row.snapshot_id,
            parent_job_id=row.parent_job_id,
            repo=RepoContext(
                id=repo.id,
                full_name=repo.full_name,
                local_path=repo.local_path,
                clone_url=repo.clone_url,
                language=repo.language,
                owner_id=repo.owner_id,
            ),
            meta=copy.deepcopy(row.metadata),
        )

    async def complete(self, job_id: str, result: dict[str, Any]) -> None:
        row = self._jobs[job_id]
        row.status = "completed"
        row.progress = 1.0
        row.completed_at = self._now()
        row.metadata = copy.deepcopy(result)

    async def fail(self, job_id: str) -> str:
        row = self._jobs[job_id]
        row.retry_count += 1
        row.locked_by = None
        row.locked_at = None
        if row.retry_count >= row.max_retries:
            row.status = "failed"
            row.completed_at = self._now()
            self._repos[row.repository_id].status = "error"
            return "failed"
        row.status = "queued"
        return "queued"

    async def link_snapshot(self, job_id: str, snapshot_id: str) -> None:
        self._jobs[job_id].snapshot_id = snapshot_id

    async def insert_snapshot(
        self,
        repository_id: str,
        commit_sha: str,
        branch: str,
        file_count: int,
        total_size_bytes: int,
    ) -> str:
        snap = _Snapshot(
            id=str(uuid.uuid4()),
            repository_id=repository_id,
            commit_sha=commit_sha,
            branch=branch,
            file_count=file_count,
            total_size_bytes=total_size_bytes,
        )
        self._snapshots.append(snap)
        return snap.id

    async def set_repo_active(
        self, repository_id: str, sha: str | None, *, touch_synced_at: bool
    ) -> None:
        repo = self._repos[repository_id]
        repo.status = "active"
        if sha is not None:
            repo.last_synced_sha = sha

    async def siblings_completed(self, parent_job_id: str, exclude_job_id: str) -> bool:
        return all(
            row.status == "completed"
            for row in self._jobs.values()
            if row.parent_job_id == parent_job_id and row.id != exclude_job_id
        )
