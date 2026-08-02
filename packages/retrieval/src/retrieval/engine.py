from __future__ import annotations

import asyncio
import time

import structlog

from .models import RetrievalHit, RetrievalResult, RetrievalTrace
from .rerank import reciprocal_rank_fusion
from .searchers.graph import GraphSearcher
from .searchers.keyword import KeywordSearcher
from .searchers.symbol import SymbolSearcher
from .searchers.vector import VectorSearcher

logger = structlog.get_logger(__name__)


class HybridRetrievalEngine:
    """Orchestrates vector, symbol, keyword, and graph retrieval.

    Every searcher runs concurrently and degrades gracefully: if a
    backing store is down, the remaining sources still answer. Results
    are fused with Reciprocal Rank Fusion and each hit records which
    strategies found it (sources) for observability.
    """

    def __init__(
        self,
        vector: VectorSearcher | None = None,
        symbol: SymbolSearcher | None = None,
        keyword: KeywordSearcher | None = None,
        graph: GraphSearcher | None = None,
    ) -> None:
        self._vector = vector or VectorSearcher()
        self._symbol = symbol or SymbolSearcher()
        self._keyword = keyword or KeywordSearcher()
        self._graph = graph or GraphSearcher()

    async def search(
        self,
        query: str,
        repository_id: str,
        limit: int = 20,
        kind_filter: str | None = None,
        include_graph_expansion: bool = True,
    ) -> RetrievalResult:
        started = time.perf_counter()
        query = query.strip()
        if not query:
            raise ValueError("query must not be empty")

        logger.info(
            "hybrid_search_start",
            repo_id=repository_id,
            query=query,
            limit=limit,
        )

        vector_future = self._vector.search(
            query, repository_id, limit=limit, kind_filter=kind_filter
        )

        symbol_future = self._symbol.search(
            query, repository_id, limit=limit, kind_filter=kind_filter
        )

        keyword_future = self._keyword.search(
            query, repository_id, limit=limit, kind_filter=kind_filter
        )

        vector_result, symbol_result, keyword_result = await asyncio.gather(
            vector_future, symbol_future, keyword_future
        )

        results = [vector_result, symbol_result, keyword_result]

        if include_graph_expansion:
            seeds = [h.symbol_id for h in symbol_result.hits[:50]]
            if not seeds:
                seeds = [h.symbol_id for h in keyword_result.hits[:10]]
            graph_result = await self._graph.search(
                query, repository_id, limit=limit, seeds=seeds
            )
            results.append(graph_result)

        fused = reciprocal_rank_fusion(results, limit=limit)

        trace = RetrievalTrace(
            query=query,
            repository_id=repository_id,
            searcher_results=results,
            fused_count=len(fused),
            total_candidates=sum(len(r.hits) for r in results),
        )

        logger.info(
            "hybrid_search_done",
            repo_id=repository_id,
            hits=len(fused),
            candidates=trace.total_candidates,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )

        return RetrievalResult(
            query=query,
            repository_id=repository_id,
            hits=fused,
            total=len(fused),
            trace=trace,
        )

    def hits_to_dict(self, hits: list[RetrievalHit]) -> list[dict]:
        return [h.to_dict() for h in hits]

    async def close(self) -> None:
        await asyncio.gather(
            self._vector.close(),
            self._symbol.close(),
            self._keyword.close(),
            self._graph.close(),
            return_exceptions=True,
        )
