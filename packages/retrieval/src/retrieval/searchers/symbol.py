from __future__ import annotations

import time

import structlog

from graph_engine import Neo4jClient

from ..models import SearcherResult, SearchSource
from .base import BaseSearcher

logger = structlog.get_logger(__name__)


class SymbolSearcher(BaseSearcher):
    """Exact and prefix symbol lookup in the Neo4j symbol index.

    Answers "is there a symbol named X" — the deterministic anchor for
    graph expansion and impact analysis.
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        self._client = client or Neo4jClient()

    @property
    def source(self) -> SearchSource:
        return SearchSource.SYMBOL

    async def search(
        self,
        query: str,
        repository_id: str,
        limit: int,
        kind_filter: str | None = None,
        seeds: list[str] | None = None,
    ) -> SearcherResult:
        started = time.perf_counter()
        try:
            exact = await self._client.execute_read(
                """
                MATCH (s:Symbol {repository_id: $repo_id})
                WHERE s.name = $name
                  AND ($kind IS NULL OR s.kind = $kind)
                RETURN s.symbol_id AS symbol_id, s.name AS name, s.kind AS kind,
                       s.signature AS signature, s.file_path AS file_path,
                       s.start_line AS start_line, s.end_line AS end_line,
                       s.parent_name AS parent_name, s.language AS language
                LIMIT $limit
                """,
                {
                    "repo_id": repository_id,
                    "name": query,
                    "kind": kind_filter,
                    "limit": max(limit, 10),
                },
            )

            prefix = await self._client.execute_read(
                """
                MATCH (s:Symbol {repository_id: $repo_id})
                WHERE s.name STARTS WITH $prefix
                  AND ($kind IS NULL OR s.kind = $kind)
                RETURN s.symbol_id AS symbol_id, s.name AS name, s.kind AS kind,
                       s.signature AS signature, s.file_path AS file_path,
                       s.start_line AS start_line, s.end_line AS end_line,
                       s.parent_name AS parent_name, s.language AS language
                ORDER BY s.name
                LIMIT $limit
                """,
                {
                    "repo_id": repository_id,
                    "prefix": query,
                    "kind": kind_filter,
                    "limit": limit,
                },
            )

            hits = [
                self._hit_from_row(r, score=1.0, sources=[self.source.value])
                for r in exact
            ]
            prefix_scores = [1.0 / (i + 2) for i in range(len(prefix))]
            hits += [
                self._hit_from_row(r, score=score, sources=[self.source.value])
                for r, score in zip(prefix, prefix_scores)
            ]
            return SearcherResult(
                source=self.source,
                hits=hits,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception as e:
            logger.warning("symbol_search_failed", repo=repository_id, error=str(e))
            return SearcherResult(
                source=self.source,
                hits=[],
                error=str(e)[:300],
                duration_ms=(time.perf_counter() - started) * 1000,
            )

    async def close(self) -> None:
        await self._client.close()
