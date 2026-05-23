from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

from parser.models import Language as LangConfig, ParsedSymbol
from shared.models.repository import SymbolKind

logger = structlog.get_logger(__name__)

KIND_MAP: dict[str, SymbolKind] = {
    "function": SymbolKind.FUNCTION,
    "class": SymbolKind.CLASS,
    "interface": SymbolKind.INTERFACE,
    "method": SymbolKind.FUNCTION,
    "type": SymbolKind.TYPE,
    "enum": SymbolKind.ENUM,
    "variable": SymbolKind.VARIABLE,
    "import": SymbolKind.IMPORT,
    "export": SymbolKind.EXPORT,
    "parameter": SymbolKind.PARAMETER,
}


class BaseSymbolExtractor(ABC):
    def __init__(self, lang_config: LangConfig):
        self.lang_config = lang_config

    @abstractmethod
    def extract(self, tree: object, source: bytes, file_path: str) -> list[ParsedSymbol]:
        ...

    @staticmethod
    def _node_text(node, source: bytes) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def _child_text(node, source: bytes, field_name: str) -> str | None:
        child = node.child_by_field_name(field_name)
        if child:
            return source[child.start_byte : child.end_byte].decode("utf-8", errors="replace")
        return None
