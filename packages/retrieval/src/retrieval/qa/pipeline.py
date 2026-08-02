from __future__ import annotations

import time

import structlog

from prompts import build_qa_messages

from ..engine import HybridRetrievalEngine
from .llm import BaseLLMClient, get_llm_client
from .models import QAAnswer, QAResult

logger = structlog.get_logger(__name__)


class QAPipeline:
    """GraphRAG pipeline: hybrid retrieval → grounded context → cited answer."""

    def __init__(
        self,
        engine: HybridRetrievalEngine,
        llm: BaseLLMClient | None = None,
        repository_name: str = "",
    ) -> None:
        self._engine = engine
        self._llm = llm or get_llm_client()
        self._repository_name = repository_name

    async def answer(
        self,
        repository_id: str,
        question: str,
        limit: int = 12,
        provider: str | None = None,
        max_tokens: int = 1024,
    ) -> QAResult:
        if provider and provider != self._llm.provider:
            self._llm = get_llm_client(provider)

        started = time.perf_counter()

        retrieval = await self._engine.search(
            question,
            repository_id,
            limit=limit,
            include_graph_expansion=True,
        )

        hits = retrieval.hits
        messages = build_qa_messages(question, [h.to_dict() for h in hits], self._repository_name)

        llm_started = time.perf_counter()
        try:
            answer_text = await self._llm.complete(
                messages,
                max_tokens=max_tokens,
                temperature=0.2,
            )
            llm_error = None
        except Exception as e:
            logger.warning("llm_complete_failed", repo=repository_id, error=str(e))
            answer_text = (
                "I could not generate an answer because the LLM provider "
                f"failed ({type(e).__name__}: {str(e)[:200]}). "
                "The retrieval results below still show what was found."
            )
            llm_error = str(e)[:300]

        llm_ms = round((time.perf_counter() - llm_started) * 1000, 2)

        context_blocks = [
            {
                "index": i,
                "kind": h.kind,
                "name": h.name,
                "file_path": h.file_path,
                "start_line": h.start_line,
                "end_line": h.end_line,
                "signature": h.signature,
                "score": h.score,
                "sources": h.sources,
            }
            for i, h in enumerate(hits, start=1)
        ]

        answer = QAAnswer(
            question=question,
            answer=answer_text,
            context_blocks=context_blocks,
            model=self._llm.model,
            provider=self._llm.provider,
        )

        logger.info(
            "qa_pipeline_done",
            repo=repository_id,
            hits=len(hits),
            llm_ms=llm_ms,
            total_ms=round((time.perf_counter() - started) * 1000, 2),
        )

        return QAResult(
            answer=answer,
            retrieval={
                "hits": [h.to_dict() for h in hits],
                "trace": retrieval.trace.to_dict(),
                "llm": {
                    "model": self._llm.model,
                    "provider": self._llm.provider,
                    "duration_ms": llm_ms,
                    "error": llm_error,
                },
            },
        )
