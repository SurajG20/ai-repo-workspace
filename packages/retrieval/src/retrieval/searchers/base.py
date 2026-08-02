from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import RetrievalHit, SearcherResult, SearchSource


class BaseSearcher(ABC):
    """Contract every retrieval searcher implements.

    A searcher answers one deterministic question (semantic similarity,
    exact symbol match, substring keyword match, or graph neighborhood
    expansion) and never mixes retrieval strategies.
    """

    @property
    @abstractmethod
    def source(self) -> SearchSource:
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        repository_id: str,
        limit: int,
        kind_filter: str | None = None,
        seeds: list[str] | None = None,
    ) -> SearcherResult:
        ...

    @staticmethod
    def _hit_from_row(row: dict, score: float = 0.0, sources: list[str] | None = None) -> RetrievalHit:
        return RetrievalHit(
            symbol_id=row.get("symbol_id") or row.get("id") or "",
            name=row.get("name", "unknown"),
            kind=row.get("kind", "symbol"),
            file_path=row.get("file_path", ""),
            signature=row.get("signature"),
            start_line=int(row.get("start_line", 0) or 0),
            end_line=int(row.get("end_line", 0) or 0),
            parent_name=row.get("parent_name"),
            language=row.get("language"),
            score=score,
            sources=sources or [],
        )
