from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from jobs import IndexingPipeline
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..dependencies import get_current_user, get_pipeline
from ..models.repository import Repository
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
    def from_model(cls, repo: Repository) -> RepositoryResponse:
        return cls(
            id=str(repo.id),
            full_name=repo.full_name,
            provider=repo.provider.value if hasattr(repo.provider, "value") else repo.provider,
            status=repo.status.value if hasattr(repo.status, "value") else repo.status,
            language=repo.language,
            description=repo.description,
            is_private=repo.is_private,
            default_branch=repo.default_branch,
            size_bytes=repo.size_bytes,
            last_synced_at=repo.last_synced_at.isoformat() if repo.last_synced_at else None,
            last_synced_sha=repo.last_synced_sha,
            created_at=repo.created_at.isoformat() if repo.created_at else "",
        )


@router.get("/stats/overview")
async def overview_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    from ..models.job import IndexingJob
    from ..models.snapshot import RepositorySnapshot

    service = RepositoryService(session)
    repos = await service.list_by_owner(user.id, limit=200, offset=0)

    def _s(v) -> str:
        return v.value if hasattr(v, "value") else str(v)

    total = len(repos)
    active = sum(1 for r in repos if _s(r.status) in ("active", "indexing"))
    status_counts: dict[str, int] = {}
    languages: dict[str, int] = {}
    for r in repos:
        status_counts[_s(r.status)] = status_counts.get(_s(r.status), 0) + 1
        if r.language:
            languages[r.language] = languages.get(r.language, 0) + 1

    files_total = 0
    snapshot_counts = 0
    if repos:
        result = await session.execute(
            sa_select(func.sum(RepositorySnapshot.file_count)).where(
                RepositorySnapshot.repository_id.in_([r.id for r in repos])
            )
        )
        files_total = int(result.scalar() or 0)
        result = await session.execute(
            sa_select(func.count(RepositorySnapshot.id)).where(
                RepositorySnapshot.repository_id.in_([r.id for r in repos])
            )
        )
        snapshot_counts = int(result.scalar() or 0)

    job_counts = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
    if repos:
        result = await session.execute(
            sa_select(IndexingJob.status, func.count(IndexingJob.id)).where(
                IndexingJob.repository_id.in_([r.id for r in repos])
            ).group_by(IndexingJob.status)
        )
        for status, count in result.all():
            job_counts[str(status)] = count

    symbols_by_kind: dict[str, int] = {}
    symbols_total = 0
    from graph_engine import Neo4jClient

    client = Neo4jClient()
    try:
        for r in repos:
            try:
                stats = await client.execute_read(
                    """
                    MATCH (s:Symbol {repository_id: $repo_id})
                    RETURN s.kind AS kind, count(s) AS count
                    """,
                    {"repo_id": str(r.id)},
                )
                for row in stats:
                    kind = row["kind"]
                    count = int(row["count"])
                    symbols_by_kind[kind] = symbols_by_kind.get(kind, 0) + count
                    symbols_total += count
            except Exception:
                continue
    finally:
        await client.close()

    return {
        "repositories_total": total,
        "repositories_active": active,
        "repositories_by_status": status_counts,
        "languages": languages,
        "files_total": files_total,
        "snapshots_total": snapshot_counts,
        "symbols_total": symbols_total,
        "symbols_by_kind": symbols_by_kind,
        "jobs": job_counts,
    }


@router.get("", response_model=list[RepositoryResponse])
async def list_repositories(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[RepositoryResponse]:
    service = RepositoryService(session)
    repos = await service.list_by_owner(user.id, limit=limit, offset=offset)
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
    pipeline: IndexingPipeline = Depends(get_pipeline),
) -> RepositoryResponse:
    service = RepositoryService(session, pipeline)

    if body.local_path:
        try:
            repo = await service.create_from_local(user.id, body.local_path, body.name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        await session.commit()
        await service.enqueue_initial_indexing(repo)
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
    pipeline: IndexingPipeline = Depends(get_pipeline),
) -> dict[str, str]:
    service = RepositoryService(session, pipeline)
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
