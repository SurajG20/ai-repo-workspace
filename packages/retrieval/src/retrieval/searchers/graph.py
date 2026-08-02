from __future__ import annotations

import time

import structlog

from graph_engine import Neo4jClient

from ..models import SearcherResult, SearchSource
from .base import BaseSearcher

logger = structlog.get_logger(__name__)


class GraphSearcher(BaseSearcher):
    """Neighborhood expansion from seed symbols in Neo4j.

    Given symbol anchors (from symbol/keyword/vector hits), return their
    direct callers, callees, and type relationships so architecture
    context rides along with every query.
    """

    def __init__(self, client: Neo4jClient | None = None) -> None:
        self._client = client or Neo4jClient()

    @property
    def source(self) -> SearchSource:
        return SearchSource.GRAPH

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
            if not seeds:
                return SearcherResult(
                    source=self.source,
                    hits=[],
                    duration_ms=(time.perf_counter() - started) * 1000,
                )

            rows = await self._client.execute_read(
                """
                MATCH (s:Symbol {repository_id: $repo_id})
                WHERE s.symbol_id IN $seeds
                MATCH (n:Symbol {repository_id: $repo_id})-[r]-(s)
                RETURN DISTINCT n.symbol_id AS symbol_id, n.name AS name,
                       n.kind AS kind, n.signature AS signature,
                       n.file_path AS file_path, n.start_line AS start_line,
                       n.end_line AS end_line, n.parent_name AS parent_name,
                       n.language AS language, type(r) AS rel
                LIMIT $limit
                """,
                {"repo_id": repository_id, "seeds": seeds[:50], "limit": limit},
            )

            seed_set = set(seeds)
            hits = []
            for r in rows:
                if r.get("symbol_id") in seed_set:
                    continue
                hits.append(
                    self._hit_from_row(
                        r,
                        score=0.5,
                        sources=[self.source.value, f"graph:{r.get('rel', '')}"],
                    )
                )
            return SearcherResult(
                source=self.source,
                hits=hits,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception as e:
            logger.warning("graph_search_failed", repo=repository_id, error=str(e))
            return SearcherResult(
                source=self.source,
                hits=[],
                error=str(e)[:300],
                duration_ms=(time.perf_counter() - started) * 1000,
            )

    async def close(self) -> None:
        await self._client.close()
