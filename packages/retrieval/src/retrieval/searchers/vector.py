from __future__ import annotations

import os
import time

import structlog

from embeddings import BaseEmbedder, OllamaEmbedder, OpenAIEmbedder, QdrantStore

from ..models import SearcherResult, SearchSource
from .base import BaseSearcher

logger = structlog.get_logger(__name__)


def _get_query_embedder(provider: str | None = None) -> BaseEmbedder:
    provider = provider or os.getenv("EMBEDDING_PROVIDER", "openai")
    if provider == "ollama":
        return OllamaEmbedder()
    return OpenAIEmbedder()


class VectorSearcher(BaseSearcher):
    """Semantic search over structurally chunked symbols in Qdrant."""

    def __init__(
        self,
        store: QdrantStore | None = None,
        embedder: BaseEmbedder | None = None,
        provider: str | None = None,
    ) -> None:
        self._store = store or QdrantStore()
        self._embedder = embedder or _get_query_embedder(provider)

    @property
    def source(self) -> SearchSource:
        return SearchSource.VECTOR

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
            vectors = await self._embedder.embed([query])
            if not vectors:
                raise RuntimeError("embedder returned no vectors")
            collection = f"repo_{repository_id}"
            results = await self._store.search(
                collection_name=collection,
                query_vector=vectors[0],
                limit=limit,
                filter_kind=kind_filter,
            )
            hits = []
            for r in results:
                hit = self._hit_from_row(r, score=float(r.get("score", 0.0)), sources=[self.source.value])
                hits.append(hit)
            return SearcherResult(
                source=self.source,
                hits=hits,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        except Exception as e:
            logger.warning("vector_search_failed", repo=repository_id, error=str(e))
            return SearcherResult(
                source=self.source,
                hits=[],
                error=str(e)[:300],
                duration_ms=(time.perf_counter() - started) * 1000,
            )

    async def close(self) -> None:
        await self._store.close()
