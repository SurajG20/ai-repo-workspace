from __future__ import annotations

import json
import os
from typing import Any

import structlog
from embeddings import EmbeddingPipeline

logger = structlog.get_logger(__name__)


async def embed_stage(
    repository_id: str,
    language: str,
    symbols: list[dict] | None = None,
    provider: str | None = None,
    data_file: str | None = None,
) -> dict[str, Any]:
    if data_file:
        logger.info("loading_parse_data_from_file", file=data_file)
        with open(data_file) as f:
            data = json.load(f)
        symbols = data.get("symbols", [])
        repository_id = data.get("repository_id", repository_id)

    embedding_provider = provider or os.getenv("EMBEDDING_PROVIDER", "openai")

    return await _embed_repository_async(
        repository_id, language, symbols or [], embedding_provider
    )


async def _embed_repository_async(
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


def _get_embedder(provider: str):
    if provider == "ollama":
        from embeddings import OllamaEmbedder
        return OllamaEmbedder()
    from embeddings import OpenAIEmbedder
    return OpenAIEmbedder()
