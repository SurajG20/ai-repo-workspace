from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shared.models.repository import SymbolKind


@dataclass
class ParsedSymbol:
    file_path: str
    name: str
    symbol_kind: SymbolKind
    signature: str | None = None
    start_line: int = 0
    end_line: int = 0
    start_col: int = 0
    end_col: int = 0
    parent_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SymbolRelationship:
    source_file: str
    source_symbol: str
    target_symbol: str
    relationship_type: str
    target_file: str | None = None
    line_number: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Language:
    name: str
    extensions: tuple[str, ...]
    grammar_file: str
    tree_sitter_name: str
