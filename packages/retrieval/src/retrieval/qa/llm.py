from __future__ import annotations

import os
from abc import ABC, abstractmethod

import httpx
import structlog

logger = structlog.get_logger(__name__)

DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "ollama": "llama3.1",
}


class BaseLLMClient(ABC):
    """Pluggable chat completion client (BYOK)."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        ...

    @property
    @abstractmethod
    def provider(self) -> str:
        ...

    @property
    @abstractmethod
    def model(self) -> str:
        ...


class OpenAILLMClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import AsyncOpenAI

        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS["openai"]
        self._client = AsyncOpenAI(
            api_key=self._api_key,
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            timeout=90.0,
            max_retries=2,
        )

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


class AnthropicLLMClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        from anthropic import AsyncAnthropic

        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS["anthropic"]
        self._client = AsyncAnthropic(
            api_key=self._api_key,
            timeout=90.0,
            max_retries=2,
        )

    @property
    def provider(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        system = "\n".join(
            m["content"] for m in messages if m["role"] == "system"
        )
        user_msgs = [
            m for m in messages if m["role"] != "system"
        ]
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or None,
            messages=user_msgs,
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        )


class OllamaLLMClient(BaseLLMClient):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._base_url = (
            base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self._model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS["ollama"]
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(180.0))

    @property
    def provider(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        response = await self._client.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            },
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")

    async def close(self) -> None:
        await self._client.aclose()


def get_llm_client(provider: str | None = None) -> BaseLLMClient:
    """Factory: provider from env LLM_PROVIDER (openai | anthropic | ollama)."""
    provider = provider or os.getenv("LLM_PROVIDER", "openai")
    if provider == "anthropic":
        return AnthropicLLMClient()
    if provider == "ollama":
        return OllamaLLMClient()
    return OpenAILLMClient()
