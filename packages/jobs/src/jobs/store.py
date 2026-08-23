from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any

from .models import ClaimedJob, Job, Stage


class RepositoryDeletedError(Exception):
    """Raised when enqueuing work for a soft-deleted repository."""


class JobStore(ABC):
    """Persistence seam for the Indexing Pipeline.

    The pipeline owns *policy* (DAG, transition rules, artifact lifecycle);
    a store owns *state* (rows, locks, timestamps). Tests run the policy
    against an in-memory adapter; production runs it against Postgres.
    """

    @abstractmethod
    async def enqueue(
        self,
        repository_id: str,
        stage: Stage,
        *,
        snapshot_id: str | None = None,
        parent_job_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Job:
        """Queue one Job. Raises RepositoryDeletedError for soft-deleted repositories."""

    @abstractmethod
    async def claim_next(self, worker_id: str, stale_after: timedelta) -> ClaimedJob | None:
        """Atomically claim the oldest queued Job.

        Reclaims stale running Jobs first (incrementing retry_count and
        failing those that exhaust retries), cancels queued Jobs belonging
        to soft-deleted repositories, then claims with exclusivity.
        """

    @abstractmethod
    async def complete(self, job_id: str, result: dict[str, Any]) -> None:
        """Mark completed with progress 1.0, storing result as job metadata."""

    @abstractmethod
    async def fail(self, job_id: str) -> str:
        """Increment retry_count; requeue or fail on exhaustion.

        On exhaustion also marks the repository 'error'.
        Returns the resulting job status ('queued' or 'failed').
        """

    @abstractmethod
    async def link_snapshot(self, job_id: str, snapshot_id: str) -> None: ...

    @abstractmethod
    async def insert_snapshot(
        self,
        repository_id: str,
        commit_sha: str,
        branch: str,
        file_count: int,
        total_size_bytes: int,
    ) -> str:
        """Insert a snapshot row, returning its id."""

    @abstractmethod
    async def set_repo_active(
        self, repository_id: str, sha: str | None, *, touch_synced_at: bool
    ) -> None: ...

    @abstractmethod
    async def siblings_completed(self, parent_job_id: str, exclude_job_id: str) -> bool:
        """True when every sibling of exclude_job_id under parent_job_id is completed."""
