from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def build_symbol_id(repository_id: str, file_path: str, symbol_name: str) -> str:
    """The one true symbol identity scheme: repo:path:name."""
    return ":".join([repository_id, file_path, symbol_name])


@dataclass
class IndexedSymbol:
    """The canonical Symbol record.

    Produced by parsing, consumed by graph sync and embedding. Every field
    is load-bearing; per-language leftovers live in `extras` and must not
    be relied on by consumers.
    """

    symbol_id: str
    repository_id: str
    snapshot_id: str | None
    name: str
    kind: str
    file_path: str
    signature: str | None = None
    start_line: int = 0
    end_line: int = 0
    start_col: int = 0
    end_col: int = 0
    parent_name: str | None = None
    is_exported: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> IndexedSymbol:
        return cls(
            symbol_id=payload["symbol_id"],
            repository_id=payload["repository_id"],
            snapshot_id=payload.get("snapshot_id"),
            name=payload["name"],
            kind=payload.get("kind", ""),
            file_path=payload.get("file_path", ""),
            signature=payload.get("signature"),
            start_line=payload.get("start_line", 0),
            end_line=payload.get("end_line", 0),
            start_col=payload.get("start_col", 0),
            end_col=payload.get("end_col", 0),
            parent_name=payload.get("parent_name"),
            is_exported=bool(payload.get("is_exported", False)),
            extras=dict(payload.get("extras") or {}),
        )


@dataclass
class SymbolRelationship:
    """The canonical Relationship record between two IndexedSymbols."""

    relationship_id: str
    repository_id: str
    snapshot_id: str | None
    source_symbol_id: str
    target_symbol_id: str
    source_file: str
    source_symbol: str
    target_symbol: str
    relationship_type: str
    target_file: str | None = None
    resolved_file: str | None = None
    line_number: int = 0
    extras: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SymbolRelationship:
        return cls(
            relationship_id=payload["relationship_id"],
            repository_id=payload["repository_id"],
            snapshot_id=payload.get("snapshot_id"),
            source_symbol_id=payload.get("source_symbol_id", ""),
            target_symbol_id=payload.get("target_symbol_id", ""),
            source_file=payload.get("source_file", ""),
            source_symbol=payload.get("source_symbol", ""),
            target_symbol=payload.get("target_symbol", ""),
            relationship_type=payload.get("relationship_type", ""),
            target_file=payload.get("target_file"),
            resolved_file=payload.get("resolved_file"),
            line_number=payload.get("line_number", 0),
            extras=dict(payload.get("extras") or {}),
        )
