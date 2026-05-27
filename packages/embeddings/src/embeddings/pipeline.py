from __future__ import annotations

import structlog
from qdrant_client.models import PointStruct

from .base import BaseEmbedder
from .openai_embedder import OpenAIEmbedder
from .ollama_embedder import OllamaEmbedder
from .qdrant_store import QdrantStore
from .chunker import chunk_from_parse_result

logger = structlog.get_logger(__name__)


def _get_embedder(provider: str) -> BaseEmbedder:
    if provider == "ollama":
        return OllamaEmbedder()
    return OpenAIEmbedder()


class EmbeddingPipeline:
    def __init__(
        self,
        embedder: BaseEmbedder | None = None,
        store: QdrantStore | None = None,
    ) -> None:
        self._embedder = embedder or _get_embedder("openai")
        self._store = store or QdrantStore()

    async def embed_and_store(
        self,
        symbols: list[dict],
        repository_id: str,
        language: str,
        collection_name: str | None = None,
    ) -> dict:
        if not symbols:
            return {"chunks": 0, "embedded": 0, "stored": 0}

        collection = collection_name or f"repo_{repository_id}"

        await self._store.ensure_collection(
            collection_name=collection,
            vector_dim=self._embedder.dimension,
        )

        texts: list[str] = []
        metas: list[dict] = []
        for sym in symbols:
            text = chunk_from_parse_result(sym)
            texts.append(text)
            metas.append({
                "symbol_id": sym.get("id", ""),
                "name": sym.get("name", "unknown"),
                "kind": sym.get("symbol_kind", "unknown"),
                "file_path": sym.get("file_path", ""),
                "signature": sym.get("signature", ""),
                "start_line": sym.get("start_line", 0),
                "end_line": sym.get("end_line", 0),
                "parent_name": sym.get("parent_name", ""),
                "language": language,
                "repository_id": repository_id,
            })

        batch_size = 50
        total_stored = 0
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_metas = metas[i : i + batch_size]

            vectors = await self._embedder.embed(batch_texts)

            points = [
                PointStruct(
                    id=m["symbol_id"],
                    vector=v,
                    payload=m,
                )
                for m, v in zip(batch_metas, vectors)
            ]
            await self._store.upsert_points(collection, points)
            total_stored += len(points)

            logger.info(
                "embed_batch_done",
                repo=repository_id,
                batch=(i // batch_size) + 1,
                stored=total_stored,
                total=len(texts),
            )

        return {
            "chunks": len(texts),
            "embedded": len(texts),
            "stored": total_stored,
            "collection": collection,
            "dimension": self._embedder.dimension,
        }

    async def close(self) -> None:
        await self._store.close()
        if hasattr(self._embedder, "close"):
            await self._embedder.close()
