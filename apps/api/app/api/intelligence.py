from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..core.database import get_db
from ..dependencies import get_current_user
from ..models.user import User
from ..services.repository import RepositoryService

router = APIRouter(prefix="/repositories/{repo_id}", tags=["intelligence"])
logger = structlog.get_logger(__name__)

DEAD_CODE_LLM_PROVIDERS = ("openai", "anthropic", "ollama")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    kind_filter: str | None = None
    include_graph_expansion: bool = True


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=12, ge=1, le=50)
    provider: str | None = None
    max_tokens: int = Field(default=1024, ge=64, le=4096)


class PRFilesRequest(BaseModel):
    files: list[str] = Field(min_length=1)
    title: str | None = None
    description: str | None = None
    summarize: bool = False
    provider: str | None = None


async def _get_repo_or_404(
    repo_id: UUID,
    user: User,
    session: AsyncSession,
):
    service = RepositoryService(session)
    repo = await service.get_by_id(repo_id, user.id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.post("/search")
async def hybrid_search(
    repo_id: UUID,
    body: SearchRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _get_repo_or_404(repo_id, user, session)

    from retrieval import HybridRetrievalEngine

    engine = HybridRetrievalEngine()
    try:
        result = await engine.search(
            body.query,
            str(repo_id),
            limit=body.limit,
            kind_filter=body.kind_filter,
            include_graph_expansion=body.include_graph_expansion,
        )
        return result.to_dict()
    finally:
        await engine.close()


@router.post("/ask")
async def ask_question(
    repo_id: UUID,
    body: AskRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = await _get_repo_or_404(repo_id, user, session)

    from retrieval import HybridRetrievalEngine, QAPipeline, get_llm_client

    llm = get_llm_client(body.provider or settings.llm_provider)

    engine = HybridRetrievalEngine()
    try:
        pipeline = QAPipeline(engine=engine, llm=llm, repository_name=repo.full_name)
        result = await pipeline.answer(
            str(repo_id),
            body.question,
            limit=body.limit,
            provider=body.provider or settings.llm_provider,
            max_tokens=body.max_tokens,
        )
        return result.to_dict()
    finally:
        await engine.close()


@router.get("/symbols")
async def get_symbols(
    repo_id: UUID,
    name: str | None = None,
    file_path: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _get_repo_or_404(repo_id, user, session)

    from graph_engine import Neo4jClient

    client = Neo4jClient()
    try:
        if name:
            rows = await client.execute_read(
                """
                MATCH (s:Symbol {repository_id: $repo_id})
                WHERE toLower(s.name) CONTAINS toLower($name)
                RETURN s.symbol_id AS symbol_id, s.name AS name, s.kind AS kind,
                       s.signature AS signature, s.file_path AS file_path,
                       s.start_line AS start_line, s.end_line AS end_line,
                       s.parent_name AS parent_name
                ORDER BY s.name
                LIMIT 100
                """,
                {"repo_id": str(repo_id), "name": name},
            )
            return rows
        if file_path:
            rows = await client.execute_read(
                """
                MATCH (m:Module {repository_id: $repo_id, path: $path})-[:CONTAINS]->(s:Symbol)
                RETURN s.symbol_id AS symbol_id, s.name AS name, s.kind AS kind,
                       s.signature AS signature, s.start_line AS start_line,
                       s.end_line AS end_line, s.parent_name AS parent_name
                ORDER BY s.start_line
                """,
                {"repo_id": str(repo_id), "path": file_path},
            )
            return rows
        raise HTTPException(status_code=400, detail="Provide name or file_path")
    finally:
        await client.close()


@router.get("/graph/call-graph")
async def call_graph(
    repo_id: UUID,
    depth: int = 3,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _get_repo_or_404(repo_id, user, session)

    from graph_engine import GraphQueries

    queries = GraphQueries()
    try:
        return await queries.get_call_graph(str(repo_id), depth=depth)
    finally:
        await queries._client.close()


@router.get("/graph/dependencies")
async def dependency_graph(
    repo_id: UUID,
    limit: int = 200,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _get_repo_or_404(repo_id, user, session)

    from graph_engine import GraphQueries

    queries = GraphQueries()
    try:
        return await queries.get_dependency_graph(str(repo_id), limit=limit)
    finally:
        await queries._client.close()


@router.get("/graph/class-hierarchy")
async def class_hierarchy(
    repo_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    await _get_repo_or_404(repo_id, user, session)

    from graph_engine import GraphQueries

    queries = GraphQueries()
    try:
        return await queries.get_class_hierarchy(str(repo_id))
    finally:
        await queries._client.close()


@router.get("/graph/stats")
async def graph_stats(
    repo_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _get_repo_or_404(repo_id, user, session)

    from graph_engine import GraphQueries

    queries = GraphQueries()
    try:
        return await queries.get_repository_stats(str(repo_id))
    finally:
        await queries._client.close()


@router.get("/dead-code")
async def dead_code(
    repo_id: UUID,
    limit: int = 200,
    ai_triage: bool = False,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _get_repo_or_404(repo_id, user, session)

    from prompts import build_dead_code_prompt
    from retrieval import DeadCodeDetector, get_llm_client

    detector = DeadCodeDetector()
    try:
        candidates = await detector.detect(str(repo_id), limit=limit)
    finally:
        await detector.close()

    triage = None
    if ai_triage and candidates:
        llm = get_llm_client(settings.llm_provider)
        if llm is None:
            triage = {
                "error": "No LLM provider configured. Set LLM_PROVIDER and its API key in .env."
            }
        else:
            try:
                prompt = build_dead_code_prompt(candidates[:80])
                raw = await llm.complete([{"role": "user", "content": prompt}], max_tokens=2048)
                triage = {"raw": raw, "model": llm.model, "provider": llm.provider}
            except Exception as e:
                triage = {"error": str(e)[:300]}

    return {
        "repository_id": str(repo_id),
        "count": len(candidates),
        "candidates": candidates,
        "ai_triage": triage,
    }


@router.post("/prs/analyze")
async def analyze_pr(
    repo_id: UUID,
    body: PRFilesRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = await _get_repo_or_404(repo_id, user, session)

    from prompts import build_pr_analysis_prompt
    from retrieval import PRImpactAnalyzer, get_llm_client

    analyzer = PRImpactAnalyzer()
    try:
        impact = await analyzer.analyze(str(repo_id), body.files)
    finally:
        await analyzer.close()

    summary = None
    if body.summarize:
        llm = get_llm_client(body.provider or settings.llm_provider)
        if llm is None:
            summary = {
                "error": "No LLM provider configured. Set LLM_PROVIDER and its API key in .env."
            }
        else:
            try:
                prompt = build_pr_analysis_prompt(
                    body.title or "",
                    body.description or "",
                    [{"path": f} for f in body.files],
                    impact["impacted_symbols"],
                )
                raw = await llm.complete([{"role": "user", "content": prompt}], max_tokens=2048)
                summary = {"text": raw, "model": llm.model, "provider": llm.provider}
            except Exception as e:
                summary = {"error": str(e)[:300]}

    return {
        "repository_id": str(repo_id),
        "repository_name": repo.full_name,
        "impact": impact,
        "summary": summary,
    }
