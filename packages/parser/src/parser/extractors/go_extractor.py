from __future__ import annotations

import structlog
from shared.models.repository import SymbolKind

from parser.base_extractor import BaseSymbolExtractor
from parser.models import ParsedSymbol

logger = structlog.get_logger(__name__)


class GoExtractor(BaseSymbolExtractor):
    def extract(self, tree: object, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(tree.root_node, source, file_path, None, symbols)
        return symbols

    def _walk(self, node, source: bytes, file_path: str, parent_name: str | None, symbols: list[ParsedSymbol]):
        node_type = node.type

        if node_type == "function_declaration":
            name = self._child_text(node, source, "name")
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.FUNCTION,
                    signature=self._extract_signature(node, source),
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    parent_name=parent_name,
                    metadata={"exported": name[0].isupper()},
                ))

        if node_type == "method_declaration":
            name = self._child_text(node, source, "name")
            if name:
                recv = node.child_by_field_name("receiver")
                struct_name = self._extract_receiver(recv, source) if recv else None
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.FUNCTION,
                    signature=self._extract_signature(node, source),
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    parent_name=struct_name or parent_name,
                    metadata={"exported": name[0].isupper(), "method": True, "receiver": struct_name},
                ))

        if node_type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    spec_name = self._child_text(child, source, "name")
                    if spec_name:
                        kind = SymbolKind.TYPE
                        spec_type = child.child_by_field_name("type")
                        if spec_type and spec_type.type == "struct_type":
                            kind = SymbolKind.CLASS
                        symbols.append(ParsedSymbol(
                            file_path=file_path, name=spec_name, symbol_kind=kind,
                            signature=None,
                            start_line=child.start_point[0] + 1, end_line=child.end_point[0] + 1,
                            start_col=child.start_point[1], end_col=child.end_point[1],
                            metadata={"exported": spec_name[0].isupper()},
                        ))

        if node_type == "const_declaration" or node_type == "var_declaration":
            for child in node.children:
                if child.type == "const_spec" or child.type == "var_spec":
                    for spec_child in child.children:
                        if spec_child.type == "identifier":
                            name = self._node_text(spec_child, source)
                            symbols.append(ParsedSymbol(
                                file_path=file_path, name=name, symbol_kind=SymbolKind.VARIABLE,
                                signature=None,
                                start_line=child.start_point[0] + 1, end_line=child.end_point[0] + 1,
                                start_col=child.start_point[1], end_col=child.end_point[1],
                                parent_name=parent_name,
                                metadata={"exported": name[0].isupper(), "const": node_type == "const_declaration"},
                            ))

        for child in node.children:
            self._walk(child, source, file_path, parent_name, symbols)

    def _extract_signature(self, node, source: bytes) -> str | None:
        text = self._node_text(node, source)
        brace = text.find("{")
        if brace > 0:
            return text[:brace].strip()
        return text[:120]

    def _extract_receiver(self, node, source: bytes) -> str | None:
        if node.type == "parameter_list":
            for child in node.children:
                if child.type == "parameter_declaration":
                    type_node = child.child_by_field_name("type")
                    if type_node:
                        return self._node_text(type_node, source)
        return None
