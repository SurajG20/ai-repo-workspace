from __future__ import annotations

from abc import ABC, abstractmethod

import structlog

from parser.models import Language as LangConfig, SymbolRelationship

logger = structlog.get_logger(__name__)


class BaseDependencyExtractor(ABC):
    def __init__(self, lang_config: LangConfig):
        self.lang_config = lang_config

    @abstractmethod
    def extract(
        self,
        tree: object,
        source: bytes,
        file_path: str,
        symbols: list["ParsedSymbol"],
    ) -> list[SymbolRelationship]:
        ...

    @staticmethod
    def _node_text(node, source: bytes) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def _find_symbol(symbols: list["ParsedSymbol"], name: str, kind: str | None = None) -> str | None:
        for s in symbols:
            if s.name == name:
                if kind is None or s.symbol_kind.value == kind:
                    return s.name
        return None
