from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SearchSource(str, Enum):
    VECTOR = "vector"
    SYMBOL = "symbol"
    KEYWORD = "keyword"
    GRAPH = "graph"


@dataclass
class RetrievalHit:
    symbol_id: str
    name: str
    kind: str
    file_path: str
    signature: str | None = None
    start_line: int = 0
    end_line: int = 0
    parent_name: str | None = None
    language: str | None = None
    score: float = 0.0
    rank: int = 0
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "signature": self.signature,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "parent_name": self.parent_name,
            "language": self.language,
            "score": round(self.score, 4),
            "sources": self.sources,
        }


@dataclass
class SearcherResult:
    source: SearchSource
    hits: list[RetrievalHit]
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class RetrievalTrace:
    query: str
    repository_id: str
    searcher_results: list[SearcherResult] = field(default_factory=list)
    fused_count: int = 0
    total_candidates: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "repository_id": self.repository_id,
            "searchers": [
                {
                    "source": r.source.value,
                    "hits": len(r.hits),
                    "error": r.error,
                    "duration_ms": round(r.duration_ms, 2),
                }
                for r in self.searcher_results
            ],
            "fused_count": self.fused_count,
            "total_candidates": self.total_candidates,
        }


@dataclass
class RetrievalResult:
    query: str
    repository_id: str
    hits: list[RetrievalHit]
    total: int
    trace: RetrievalTrace

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "repository_id": self.repository_id,
            "total": self.total,
            "hits": [h.to_dict() for h in self.hits],
            "trace": self.trace.to_dict(),
        }
