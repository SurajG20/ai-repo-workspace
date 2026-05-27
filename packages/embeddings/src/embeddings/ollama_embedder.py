from __future__ import annotations

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


class OllamaEmbedder(BaseEmbedder):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")).rstrip("/")
        self._model = model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))

    @property
    def dimension(self) -> int:
        return OLLAMA_DIMENSIONS.get(self._model, 768)

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for text in texts:
            response = await self._client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            embeddings.append(data["embedding"])

        return embeddings

    async def close(self) -> None:
        await self._client.aclose()
