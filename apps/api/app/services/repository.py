from __future__ import annotations

import os
import uuid
from datetime import UTC
from pathlib import Path

import structlog
from jobs import IndexingPipeline, Job, Stage
from shared.models.repository import ProviderType, RepositoryStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.repository import Repository, RepositoryLanguage

logger = structlog.get_logger(__name__)


class RepositoryService:
    def __init__(self, session: AsyncSession, pipeline: IndexingPipeline | None = None) -> None:
        self.session = session
        self.pipeline = pipeline

    def _require_pipeline(self) -> IndexingPipeline:
        if self.pipeline is None:
            raise RuntimeError(
                "RepositoryService requires a pipeline to enqueue jobs; "
                "construct it with pipeline=Depends(get_pipeline)"
            )
        return self.pipeline

    def _repo_path(self, repo_id: str) -> str:
        return os.path.join(settings.repo_storage_path, repo_id)

    async def create_from_github(
        self,
        owner_id: uuid.UUID,
        github_repo: dict,
    ) -> Repository:
        """Persist a repository from GitHub metadata.

        Does NOT enqueue indexing: callers must commit first, then call
        enqueue_initial_indexing(repo).
        """
        repo_id = uuid.uuid4()
        repo = Repository(
            id=repo_id,
            owner_id=owner_id,
            provider=ProviderType.GITHUB,
            provider_id=str(github_repo["id"]),
            full_name=github_repo["full_name"],
            clone_url=github_repo["clone_url"],
            local_path=self._repo_path(str(repo_id)),
            default_branch=github_repo.get("default_branch", "main"),
            language=github_repo.get("language"),
            description=github_repo.get("description"),
            is_private=github_repo.get("private", False),
            size_bytes=github_repo.get("size", 0),
            status=RepositoryStatus.PENDING,
            metadata_={
                "stars": github_repo.get("stargazers_count", 0),
                "forks": github_repo.get("forks_count", 0),
                "topics": github_repo.get("topics", []),
                "html_url": github_repo.get("html_url", ""),
            },
        )
        self.session.add(repo)
        await self.session.flush()

        if lang := github_repo.get("language"):
            self.session.add(
                RepositoryLanguage(repository_id=repo.id, language=lang, percentage=100.0)
            )

        return repo

    async def create_from_local(
        self,
        owner_id: uuid.UUID,
        local_path: str,
        name: str | None = None,
    ) -> Repository:
        resolved = Path(local_path).resolve()
        if not resolved.exists():
            raise ValueError(f"Path does not exist: {local_path}")
        if not resolved.is_dir():
            raise ValueError(f"Path is not a directory: {local_path}")
        if resolved.parent != resolved and not resolved.exists():
            raise ValueError(f"Path does not exist: {local_path}")

        path = str(resolved)
        name = name or resolved.name
        repo = Repository(
            id=uuid.uuid4(),
            owner_id=owner_id,
            provider=ProviderType.LOCAL,
            full_name=name,
            local_path=path,
            status=RepositoryStatus.ACTIVE,
        )
        self.session.add(repo)
        await self.session.flush()

        return repo

    async def get_by_id(self, repo_id: uuid.UUID, owner_id: uuid.UUID) -> Repository | None:
        stmt = select(Repository).where(
            Repository.id == repo_id,
            Repository.owner_id == owner_id,
            Repository.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(
        self, owner_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[Repository]:
        stmt = (
            select(Repository)
            .where(Repository.owner_id == owner_id, Repository.deleted_at.is_(None))
            .order_by(Repository.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, repo: Repository) -> None:
        from datetime import datetime
        repo.deleted_at = datetime.now(UTC)
        repo.status = RepositoryStatus.ARCHIVED
        await self.session.flush()

    async def trigger_sync(self, repo: Repository) -> Job:
        """Queue a fresh indexing pass for an already-committed repository."""
        pipeline = self._require_pipeline()
        if repo.clone_url:
            return await pipeline.enqueue(
                str(repo.id),
                Stage.CLONE,
                metadata={
                    "clone_url": repo.clone_url,
                    "local_path": repo.local_path,
                },
            )
        return await pipeline.enqueue(str(repo.id), Stage.SNAPSHOT)

    async def enqueue_initial_indexing(self, repo: Repository) -> Job:
        """Queue the first indexing pass.

        Callers must commit the repository first: the pipeline validates
        visibility of the repository row on its own connection.
        """
        return await self.trigger_sync(repo)
