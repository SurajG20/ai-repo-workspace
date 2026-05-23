from __future__ import annotations

from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies import get_current_user
from ..models.repository import Repository, RepositoryStatus
from ..models.user import User
from ..services.repository import RepositoryService

router = APIRouter(prefix="/repositories", tags=["repositories"])
logger = structlog.get_logger(__name__)


class RepositoryCreateRequest(BaseModel):
    full_name: str | None = None
    github_url: str | None = None
    local_path: str | None = None
    name: str | None = None


class RepositoryResponse(BaseModel):
    id: str
    full_name: str
    provider: str
    status: str
    language: str | None
    description: str | None
    is_private: bool
    default_branch: str
    size_bytes: int
    last_synced_at: str | None
    last_synced_sha: str | None
    created_at: str

    @classmethod
    def from_model(cls, repo: Repository) -> "RepositoryResponse":
        return cls(
            id=str(repo.id),
            full_name=repo.full_name,
            provider=repo.provider.value,
            status=repo.status.value,
            language=repo.language,
            description=repo.description,
            is_private=repo.is_private,
            default_branch=repo.default_branch,
            size_bytes=repo.size_bytes,
            last_synced_at=repo.last_synced_at.isoformat() if repo.last_synced_at else None,
            last_synced_sha=repo.last_synced_sha,
            created_at=repo.created_at.isoformat() if repo.created_at else "",
        )


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[RepositoryResponse]:
    service = RepositoryService(session)
    repos = await service.list_by_owner(user.id)
    return [RepositoryResponse.from_model(r) for r in repos]


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    service = RepositoryService(session)
    repo = await service.get_by_id(repo_id, user.id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return RepositoryResponse.from_model(repo)


@router.post("", response_model=RepositoryResponse, status_code=201)
async def create_repository(
    body: RepositoryCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RepositoryResponse:
    service = RepositoryService(session)

    if body.local_path:
        repo = await service.create_from_local(user.id, body.local_path, body.name)
        await session.commit()
        return RepositoryResponse.from_model(repo)

    if body.github_url:
        raise HTTPException(
            status_code=400,
            detail="GitHub URL ingestion requires OAuth token. Use /auth/github/login first.",
        )

    raise HTTPException(status_code=400, detail="Provide github_url or local_path")


@router.post("/{repo_id}/sync")
async def sync_repository(
    repo_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    service = RepositoryService(session)
    repo = await service.get_by_id(repo_id, user.id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    await service.trigger_sync(repo)
    await session.commit()
    return {"status": "queued", "repository_id": str(repo_id)}


@router.delete("/{repo_id}")
async def delete_repository(
    repo_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    service = RepositoryService(session)
    repo = await service.get_by_id(repo_id, user.id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    await service.soft_delete(repo)
    await session.commit()
    return {"status": "deleted"}
