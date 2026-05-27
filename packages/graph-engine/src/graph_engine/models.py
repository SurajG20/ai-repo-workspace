from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RelationshipType(str, Enum):
    CONTAINS = "CONTAINS"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    INSTANTIATES = "INSTANTIATES"
    IMPORTS = "IMPORTS"
    IMPORTS_MODULE = "IMPORTS_MODULE"
    BELONGS_TO = "BELONGS_TO"
    USES = "USES"
    EXPORTS = "EXPORTS"
    PARAM_OF = "PARAM_OF"


@dataclass
class GraphSymbol:
    symbol_id: str
    name: str
    kind: str
    file_path: str
    language: str
    repository_id: str
    signature: str | None = None
    start_line: int = 0
    end_line: int = 0
    start_col: int = 0
    end_col: int = 0
    parent_name: str | None = None
    is_exported: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphRelationship:
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    source_file: str | None = None
    target_file: str | None = None
    line_number: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
