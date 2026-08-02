from __future__ import annotations

import asyncio
import os
import structlog
import httpx

from .base import BaseEmbedder

logger = structlog.get_logger(__name__)

OLLAMA_DIMENSIONS: dict[str, int] = {
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "all-minilm": 384,
    "bge-large": 1024,
}

_MAX_CONCURRENT = 5


class OllamaEmbedder(BaseEmbedder):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")).rstrip("/")
        self._model = model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT)

    @property
    def dimension(self) -> int:
        return OLLAMA_DIMENSIONS.get(self._model, 768)

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def _embed_one(self, text: str) -> list[float]:
        async with self._semaphore:
            response = await self._client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        tasks = [self._embed_one(t) for t in texts]
        return await asyncio.gather(*tasks)

    async def close(self) -> None:
        await self._client.aclose()
