from __future__ import annotations

import structlog

from parser.base_extractor import BaseSymbolExtractor
from parser.models import ParsedSymbol
from shared.models.repository import SymbolKind

logger = structlog.get_logger(__name__)


class JavaExtractor(BaseSymbolExtractor):
    def extract(self, tree: object, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(tree.root_node, source, file_path, None, symbols)
        return symbols

    def _walk(self, node, source: bytes, file_path: str, parent_name: str | None, symbols: list[ParsedSymbol]):
        node_type = node.type

        if node_type == "method_declaration":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.FUNCTION,
                    signature=self._extract_signature(node, source),
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    parent_name=parent_name,
                    metadata={"visibility": self._extract_visibility(node, source)},
                ))

        if node_type == "constructor_declaration":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.FUNCTION,
                    signature=self._extract_signature(node, source),
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    parent_name=parent_name,
                    metadata={"constructor": True},
                ))

        if node_type == "class_declaration":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.CLASS,
                    signature=None,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    metadata={"visibility": self._extract_visibility(node, source)},
                ))
                body = node.child_by_field_name("body")
                if body is not None:
                    for child in body.children:
                        self._walk(child, source, file_path, name, symbols)
                return

        if node_type == "interface_declaration":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.INTERFACE,
                    signature=None,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    metadata={"visibility": self._extract_visibility(node, source)},
                ))

        if node_type == "enum_declaration":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.ENUM,
                    signature=None,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    metadata={"visibility": self._extract_visibility(node, source)},
                ))

        if node_type == "field_declaration":
            for child in node.children:
                if child.type == "variable_declarator":
                    name = self._child_text(child, source, "name")
                    if name:
                        symbols.append(ParsedSymbol(
                            file_path=file_path, name=name, symbol_kind=SymbolKind.VARIABLE,
                            signature=None,
                            start_line=child.start_point[0] + 1, end_line=child.end_point[0] + 1,
                            start_col=child.start_point[1], end_col=child.end_point[1],
                            parent_name=parent_name,
                            metadata={"visibility": self._extract_visibility(node, source)},
                        ))

        for child in node.children:
            self._walk(child, source, file_path, parent_name, symbols)

    def _extract_visibility(self, node, source: bytes) -> str:
        for child in node.children:
            if child.type == "modifier":
                text = self._node_text(child, source)
                if text in ("public", "private", "protected"):
                    return text
        return "package"

    def _extract_signature(self, node, source: bytes) -> str | None:
        text = self._node_text(node, source)
        brace = text.find("{")
        if brace > 0:
            return text[:brace].strip()
        return text[:120]
