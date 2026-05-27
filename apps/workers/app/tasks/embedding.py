from __future__ import annotations

import os
import asyncio
from typing import Any

import structlog

from embeddings import EmbeddingPipeline

from ..main import app

logger = structlog.get_logger(__name__)


@app.task(name="embed_repository", bind=True, max_retries=2)
def embed_repository(
    self,
    repository_id: str,
    language: str,
    symbols: list[dict],
    provider: str | None = None,
) -> dict[str, Any]:
    embedding_provider = provider or os.getenv("EMBEDDING_PROVIDER", "openai")

    return asyncio.run(
        _embed_repository_async(
            self, repository_id, language, symbols, embedding_provider
        )
    )


async def _embed_repository_async(
    self,
    repository_id: str,
    language: str,
    symbols: list[dict],
    provider: str,
) -> dict[str, Any]:
    logger.info(
        "embed_repository_start",
        repo_id=repository_id,
        symbols=len(symbols),
        provider=provider,
    )

    try:
        pipeline = EmbeddingPipeline()

        pipeline._embedder = _get_embedder(provider)

        result = await pipeline.embed_and_store(
            symbols=symbols,
            repository_id=repository_id,
            language=language,
        )

        await pipeline.close()

        logger.info(
            "embed_repository_done",
            repo_id=repository_id,
            stored=result["stored"],
            collection=result["collection"],
        )

        return {"status": "completed", **result}

    except Exception as e:
        logger.error("embed_repository_error", repo_id=repository_id, error=str(e))
        raise self.retry(exc=e)


def _get_embedder(provider: str):
    if provider == "ollama":
        from embeddings import OllamaEmbedder
        return OllamaEmbedder()
    from embeddings import OpenAIEmbedder
    return OpenAIEmbedder()
