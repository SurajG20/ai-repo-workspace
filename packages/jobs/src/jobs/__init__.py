from __future__ import annotations

from .dag import NEXT_STAGES, TERMINAL_STAGES
from .memory_store import MemoryJobStore
from .models import ClaimedJob, Job, RepoContext, Stage
from .pipeline import DEFAULT_STALE_AFTER, IndexingPipeline
from .store import JobStore, RepositoryDeletedError

__all__ = [
    "ClaimedJob",
    "DEFAULT_STALE_AFTER",
    "IndexingPipeline",
    "Job",
    "JobStore",
    "MemoryJobStore",
    "NEXT_STAGES",
    "PostgresJobStore",
    "RepoContext",
    "RepositoryDeletedError",
    "Stage",
    "TERMINAL_STAGES",
]


def __getattr__(name: str):  # noqa: ANN202 - PEP 562
    if name == "PostgresJobStore":
        from .postgres_store import PostgresJobStore

        return PostgresJobStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
