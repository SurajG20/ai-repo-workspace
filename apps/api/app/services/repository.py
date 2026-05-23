from __future__ import annotations

import os
import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.repository import JobType, ProviderType, RepositoryStatus

from ..config import settings
from ..models.job import IndexingJob
from ..models.repository import Repository, RepositoryLanguage
from ..models.snapshot import RepositorySnapshot

logger = structlog.get_logger(__name__)


class RepositoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _repo_path(self, repo_id: str) -> str:
        return os.path.join(settings.repo_storage_path, repo_id)

    async def create_from_github(
        self,
        owner_id: uuid.UUID,
        github_repo: dict,
    ) -> Repository:
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
            self.session.add(RepositoryLanguage(repository_id=repo.id, language=lang, percentage=100.0))

        await self._enqueue_clone_job(repo)
        return repo

    async def create_from_local(
        self,
        owner_id: uuid.UUID,
        local_path: str,
        name: str | None = None,
    ) -> Repository:
        repo_id = uuid.uuid4()
        path = local_path
        name = name or os.path.basename(path.rstrip("/").rstrip("\\"))
        repo = Repository(
            id=repo_id,
            owner_id=owner_id,
            provider=ProviderType.LOCAL,
            full_name=name,
            local_path=path,
            status=RepositoryStatus.ACTIVE,
        )
        self.session.add(repo)
        await self.session.flush()

        await self._enqueue_snapshot_job(repo)
        return repo

    async def get_by_id(self, repo_id: uuid.UUID, owner_id: uuid.UUID) -> Optional[Repository]:
        stmt = select(Repository).where(
            Repository.id == repo_id,
            Repository.owner_id == owner_id,
            Repository.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_owner(self, owner_id: uuid.UUID) -> list[Repository]:
        stmt = (
            select(Repository)
            .where(Repository.owner_id == owner_id, Repository.deleted_at.is_(None))
            .order_by(Repository.updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def soft_delete(self, repo: Repository) -> None:
        from datetime import datetime, timezone
        repo.deleted_at = datetime.now(timezone.utc)
        repo.status = RepositoryStatus.ARCHIVED
        await self.session.flush()

    async def trigger_sync(self, repo: Repository) -> IndexingJob:
        await self._enqueue_snapshot_job(repo)
        return await self._enqueue_clone_job(repo)

    async def _enqueue_clone_job(self, repo: Repository) -> IndexingJob:
        job = IndexingJob(
            repository_id=repo.id,
            job_type=JobType.CLONE,
            metadata_={"clone_url": repo.clone_url, "local_path": repo.local_path},
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def _enqueue_snapshot_job(self, repo: Repository) -> IndexingJob:
        job = IndexingJob(
            repository_id=repo.id,
            job_type=JobType.SNAPSHOT,
        )
        self.session.add(job)
        await self.session.flush()
        return job
