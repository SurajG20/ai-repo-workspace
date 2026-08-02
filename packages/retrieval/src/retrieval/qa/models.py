from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QAAnswer:
    """A single grounded Q&A response with retrievable citations."""

    question: str
    answer: str
    context_blocks: list[dict[str, Any]] = field(default_factory=list)
    model: str | None = None
    provider: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "context_blocks": self.context_blocks,
            "model": self.model,
            "provider": self.provider,
        }


@dataclass
class QAResult:
    """Q&A pipeline output: answer plus the retrieval trace behind it."""

    answer: QAAnswer
    retrieval: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer.to_dict(),
            "retrieval": self.retrieval,
        }
