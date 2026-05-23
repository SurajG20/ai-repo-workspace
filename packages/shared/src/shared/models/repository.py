from __future__ import annotations

from enum import Enum


class RepositoryStatus(str, Enum):
    ACTIVE = "active"
    INDEXING = "indexing"
    ERROR = "error"
    ARCHIVED = "archived"


class IndexingJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
