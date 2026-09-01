from __future__ import annotations

import os

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

logger = structlog.get_logger(__name__)


class QdrantStore:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        api_key: str | None = None,
    ) -> None:
        self._host = host or os.getenv("QDRANT_HOST", "qdrant")
        self._port = port or int(os.getenv("QDRANT_PORT", "6333"))
        self._api_key = api_key or os.getenv("QDRANT_API_KEY", "") or None
        self._client = AsyncQdrantClient(
            host=self._host,
            port=self._port,
            api_key=self._api_key,
            timeout=30.0,
        )

    async def ensure_collection(
        self,
        collection_name: str,
        vector_dim: int,
        recreate: bool = False,
    ) -> None:
        exists = await self._client.collection_exists(collection_name)

        if exists and recreate:
            await self._client.delete_collection(collection_name)
            exists = False

        if not exists:
            await self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("collection_created", name=collection_name, dim=vector_dim)

    async def upsert_points(
        self,
        collection_name: str,
        points: list[PointStruct],
    ) -> int:
        if not points:
            return 0

        batch_size = 200
        total = 0

        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            await self._client.upsert(
                collection_name=collection_name,
                points=batch,
                wait=True,
            )
            total += len(batch)

        logger.info("upsert_points_done", collection=collection_name, count=total)
        return total

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filter_kind: str | None = None,
    ) -> list[dict]:
        query_filter = None
        if filter_kind:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="kind",
                        match=MatchValue(value=filter_kind),
                    )
                ]
            )

        results = await self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
        )

        return [
            {
                "id": p.id,
                "score": p.score,
                **{
                    k: p.payload.get(k)
                    for k in (
                        "name", "kind", "file_path", "signature",
                        "start_line", "end_line", "parent_name",
                        "language", "repository_id",
                    )
                },
            }
            for p in results.points
        ]

    async def delete_repository(self, collection_name: str, repository_id: str) -> int:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        await self._client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="repository_id",
                        match=MatchValue(value=repository_id),
                    )
                ]
            ),
        )
        logger.info("delete_repository", collection=collection_name, repo=repository_id)
        return 0

    async def count(self, collection_name: str) -> int:
        info = await self._client.get_collection(collection_name)
        return info.points_count

    async def close(self) -> None:
        await self._client.close()
