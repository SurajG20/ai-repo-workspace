from __future__ import annotations

"""Promotion of parser-internal records to the canonical shared contract.

This module is the single place where parser vocabulary (ParsedSymbol,
SymbolRelationship, per-language export flags) becomes the IndexedSymbol /
SymbolRelationship contract consumed by graph sync and embedding.
"""

import uuid

from shared.models.symbol import (
    IndexedSymbol,
    SymbolRelationship,
    build_symbol_id,
)

from .models import ParsedSymbol, SymbolRelationship

__all__ = [
    "build_symbol_id",
    "derive_is_exported",
    "to_indexed_relationship",
    "to_indexed_symbol",
]


def derive_is_exported(parsed: ParsedSymbol, language: str) -> bool:
    """What 'importable from outside the module' means for each language."""
    meta = parsed.metadata
    if language in ("typescript", "tsx", "javascript"):
        return bool(meta.get("exported", False))
    if language == "go":
        return bool(meta.get("exported", False))
    if language == "rust":
        return bool(meta.get("public", False))
    if language == "java":
        return meta.get("visibility") == "public"
    if language == "python":
        return not parsed.name.startswith("_")
    return False


def to_indexed_symbol(
    parsed: ParsedSymbol,
    *,
    repository_id: str,
    snapshot_id: str | None,
    language: str | None = None,
) -> IndexedSymbol:
    return IndexedSymbol(
        symbol_id=build_symbol_id(repository_id, parsed.file_path, parsed.name),
        repository_id=repository_id,
        snapshot_id=snapshot_id,
        name=parsed.name,
        kind=parsed.symbol_kind.value
        if hasattr(parsed.symbol_kind, "value")
        else str(parsed.symbol_kind),
        file_path=parsed.file_path,
        signature=parsed.signature,
        start_line=parsed.start_line,
        end_line=parsed.end_line,
        start_col=parsed.start_col,
        end_col=parsed.end_col,
        parent_name=parsed.parent_name,
        is_exported=(
            parsed.is_exported
            if parsed.is_exported is not None
            else (derive_is_exported(parsed, language) if language else False)
        ),
        extras=dict(parsed.metadata),
    )


def to_indexed_relationship(
    parsed: SymbolRelationship,
    *,
    repository_id: str,
    snapshot_id: str | None,
    resolved_target_file: str | None = None,
) -> SymbolRelationship:
    return SymbolRelationship(
        relationship_id=str(uuid.uuid4()),
        repository_id=repository_id,
        snapshot_id=snapshot_id,
        source_symbol_id=parsed.source_symbol_id
        or build_symbol_id(repository_id, parsed.source_file, parsed.source_symbol),
        target_symbol_id=parsed.target_symbol_id
        or build_symbol_id(
            repository_id,
            resolved_target_file or parsed.target_file or parsed.source_file,
            parsed.target_symbol,
        ),
        source_file=parsed.source_file,
        source_symbol=parsed.source_symbol,
        target_symbol=parsed.target_symbol,
        relationship_type=parsed.relationship_type,
        target_file=parsed.target_file,
        resolved_file=resolved_target_file,
        line_number=parsed.line_number,
        extras=dict(parsed.metadata),
    )
