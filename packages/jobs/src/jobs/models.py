from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Stage(str, Enum):
    CLONE = "clone"
    SNAPSHOT = "snapshot"
    PARSE = "parse"
    GRAPH_SYNC = "graph_sync"
    EMBED = "embed"


@dataclass(slots=True)
class RepoContext:
    """The repository facts a stage needs, captured at claim time."""

    id: str
    full_name: str
    local_path: str | None
    clone_url: str | None
    language: str | None
    owner_id: str | None = None


@dataclass(slots=True)
class Job:
    id: str
    repository_id: str
    stage: Stage
    status: str
    snapshot_id: str | None = None
    parent_job_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ClaimedJob:
    job_id: str
    repository_id: str
    stage: Stage
    attempt: int
    repo: RepoContext
    meta: dict[str, Any] = field(default_factory=dict)
    snapshot_id: str | None = None
    parent_job_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "repository_id": self.repository_id,
            "stage": self.stage.value,
            "attempt": self.attempt,
            "snapshot_id": self.snapshot_id,
            "parent_job_id": self.parent_job_id,
            "repo": {
                "id": self.repo.id,
                "full_name": self.repo.full_name,
                "local_path": self.repo.local_path,
                "clone_url": self.repo.clone_url,
                "language": self.repo.language,
                "owner_id": self.repo.owner_id,
            },
            "meta": self.meta,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ClaimedJob:
        repo = payload["repo"]
        return cls(
            job_id=payload["job_id"],
            repository_id=payload["repository_id"],
            stage=Stage(payload["stage"]),
            attempt=payload["attempt"],
            snapshot_id=payload.get("snapshot_id"),
            parent_job_id=payload.get("parent_job_id"),
            repo=RepoContext(
                id=repo["id"],
                full_name=repo["full_name"],
                local_path=repo.get("local_path"),
                clone_url=repo.get("clone_url"),
                language=repo.get("language"),
                owner_id=repo.get("owner_id"),
            ),
            meta=dict(payload.get("meta") or {}),
        )
