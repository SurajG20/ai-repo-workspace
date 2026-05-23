from __future__ import annotations

import structlog

from parser.base_extractor import BaseSymbolExtractor
from parser.models import ParsedSymbol
from shared.models.repository import SymbolKind

logger = structlog.get_logger(__name__)


class RustExtractor(BaseSymbolExtractor):
    def extract(self, tree: object, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(tree.root_node, source, file_path, None, symbols)
        return symbols

    def _walk(self, node, source: bytes, file_path: str, parent_name: str | None, symbols: list[ParsedSymbol]):
        node_type = node.type

        if node_type == "function_item":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.FUNCTION,
                    signature=self._extract_signature(node, source),
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    parent_name=parent_name,
                    metadata={"public": self._node_text(node, source).startswith("pub")},
                ))

        if node_type == "struct_item":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.CLASS,
                    signature=None,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    metadata={"public": self._node_text(node, source).startswith("pub")},
                ))

        if node_type == "impl_item":
            type_node = node.child_by_field_name("type")
            impl_name = self._node_text(type_node, source) if type_node else None
            body = node.child_by_field_name("body")
            if body and impl_name:
                for child in body.children:
                    self._walk(child, source, file_path, impl_name, symbols)

        if node_type == "enum_item":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.ENUM,
                    signature=None,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    metadata={"public": self._node_text(node, source).startswith("pub")},
                ))

        if node_type == "trait_item":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.INTERFACE,
                    signature=None,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    metadata={"public": self._node_text(node, source).startswith("pub")},
                ))

        if node_type == "let_declaration" and parent_name is None:
            pattern = node.child_by_field_name("pattern")
            if pattern and pattern.type == "identifier":
                name = self._node_text(pattern, source)
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.VARIABLE,
                    signature=None,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                ))

        for child in node.children:
            self._walk(child, source, file_path, parent_name, symbols)

    def _extract_signature(self, node, source: bytes) -> str | None:
        text = self._node_text(node, source)
        brace = text.find("{")
        if brace > 0:
            return text[:brace].strip()
        return text[:120]
