from __future__ import annotations

import time

import structlog
from graph_engine import Neo4jClient

logger = structlog.get_logger(__name__)


class PRImpactAnalyzer:
    """Deterministic impact analysis for a PR's changed files.

    Changed files → their symbols → reverse graph traversal to find
    callers, implementors, and importing modules. Used to ground LLM
    PR summaries in real dependency data.
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        self._client = client or Neo4jClient()

    async def analyze(
        self,
        repository_id: str,
        file_paths: list[str],
        limit: int = 200,
    ) -> dict:
        started = time.perf_counter()
        try:
            changed_symbols = await self._symbols_in_files(repository_id, file_paths)

            impacted = await self._impacted_symbols(
                repository_id, [s["symbol_id"] for s in changed_symbols], limit
            )

            impacted_modules = await self._impacted_modules(
                repository_id, file_paths, limit
            )

            result = {
                "changed_files": file_paths,
                "changed_symbols": changed_symbols,
                "impacted_symbols": impacted,
                "impacted_modules": impacted_modules,
                "blast_radius": len(impacted),
            }
            logger.info(
                "pr_impact_analyzed",
                repo=repository_id,
                changed=len(changed_symbols),
                impacted=len(impacted),
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )
            return result
        except Exception as e:
            logger.warning("pr_impact_analysis_failed", repo=repository_id, error=str(e))
            return {
                "changed_files": file_paths,
                "changed_symbols": [],
                "impacted_symbols": [],
                "impacted_modules": [],
                "blast_radius": 0,
                "error": str(e)[:300],
            }

    async def _symbols_in_files(self, repository_id: str, file_paths: list[str]) -> list[dict]:
        if not file_paths:
            return []
        return await self._client.execute_read(
            """
            MATCH (s:Symbol {repository_id: $repo_id})
            WHERE s.file_path IN $paths
            RETURN s.symbol_id AS symbol_id, s.name AS name, s.kind AS kind,
                   s.file_path AS file_path, s.signature AS signature,
                   s.start_line AS start_line, s.end_line AS end_line
            ORDER BY s.file_path, s.start_line
            """,
            {"repo_id": repository_id, "paths": file_paths},
        )

    async def _impacted_symbols(
        self, repository_id: str, symbol_ids: list[str], limit: int
    ) -> list[dict]:
        if not symbol_ids:
            return []
        return await self._client.execute_read(
            """
            MATCH (t:Symbol {repository_id: $repo_id})
            WHERE t.symbol_id IN $ids
            MATCH (caller:Symbol {repository_id: $repo_id})-[r]-(t)
            WHERE caller.symbol_id <> t.symbol_id
            RETURN DISTINCT caller.symbol_id AS symbol_id, caller.name AS name,
                   caller.kind AS kind, caller.file_path AS file_path,
                   caller.start_line AS start_line, caller.end_line AS end_line,
                   collect(DISTINCT type(r)) AS link_types
            ORDER BY caller.file_path, caller.start_line
            LIMIT $limit
            """,
            {"repo_id": repository_id, "ids": symbol_ids, "limit": limit},
        )

    async def _impacted_modules(
        self, repository_id: str, file_paths: list[str], limit: int
    ) -> list[dict]:
        if not file_paths:
            return []
        return await self._client.execute_read(
            """
            MATCH (m:Module {repository_id: $repo_id})
            WHERE m.path IN $paths
            MATCH (m)<-[r:IMPORTS_MODULE]-(importer:Module {repository_id: $repo_id})
            RETURN importer.path AS importer, m.path AS imported
            ORDER BY importer
            LIMIT $limit
            """,
            {"repo_id": repository_id, "paths": file_paths, "limit": limit},
        )

    async def close(self) -> None:
        await self._client.close()
