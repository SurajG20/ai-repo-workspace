from __future__ import annotations

import os
import structlog
from openai import AsyncOpenAI

from .base import BaseEmbedder

logger = structlog.get_logger(__name__)

OPENAI_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbedder(BaseEmbedder):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self._base_url = base_url or os.getenv("OPENAI_BASE_URL", None)
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=60.0,
                max_retries=2,
            )
        return self._client

    @property
    def dimension(self) -> int:
        return OPENAI_DIMENSIONS.get(self._model, 1536)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        client = self._get_client()
        response = await client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [d.embedding for d in response.data]
