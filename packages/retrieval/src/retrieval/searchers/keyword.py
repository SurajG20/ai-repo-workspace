from __future__ import annotations

import time

import structlog
from graph_engine import Neo4jClient

from ..models import SearcherResult, SearchSource
from .base import BaseSearcher

logger = structlog.get_logger(__name__)


class KeywordSearcher(BaseSearcher):
    """Substring match over symbol names, signatures, and file paths.

    Catches results semantic search can miss: identifiers, camelCase
    fragments, file names, and domain jargon.
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        self._client = client or Neo4jClient()

    @property
    def source(self) -> SearchSource:
        return SearchSource.KEYWORD

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
            pattern = f"%{query.lower()}%"
            rows = await self._client.execute_read(
                """
                MATCH (s:Symbol {repository_id: $repo_id})
                WHERE (toLower(s.name) CONTAINS $pattern
                   OR toLower(coalesce(s.signature, '')) CONTAINS $pattern
                   OR toLower(s.file_path) CONTAINS $pattern)
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
                    "pattern": pattern,
                    "kind": kind_filter,
                    "limit": limit,
                },
            )
            hits = [
                self._hit_from_row(r, score=1.0 / (i + 1), sources=[self.source.value])
                for i, r in enumerate(rows)
            ]
            return SearcherResult(
                source=self.source,
                hits=hits,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception as e:
            logger.warning("keyword_search_failed", repo=repository_id, error=str(e))
            return SearcherResult(
                source=self.source,
                hits=[],
                error=str(e)[:300],
                duration_ms=(time.perf_counter() - started) * 1000,
            )

    async def close(self) -> None:
        await self._client.close()
