from __future__ import annotations

import structlog
from shared.models.repository import SymbolKind

from parser.base_extractor import BaseSymbolExtractor
from parser.models import ParsedSymbol

logger = structlog.get_logger(__name__)

FUNC_NODES = {"function_declaration", "function", "method_definition", "arrow_function"}
CLASS_NODES = {"class_declaration", "class"}
IFACE_NODES = {"interface_declaration"}
ENUM_NODES = {"enum_declaration"}
TYPE_NODES = {"type_alias_declaration"}


class TypeScriptExtractor(BaseSymbolExtractor):
    def extract(self, tree: object, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(tree.root_node, source, file_path, None, symbols)
        return symbols

    def _walk(self, node, source: bytes, file_path: str, parent_name: str | None, symbols: list[ParsedSymbol]):
        node_type = node.type

        if node_type in FUNC_NODES:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = self._node_text(name_node, source)
                is_export = self._is_exported(node)
                symbols.append(ParsedSymbol(
                    file_path=file_path,
                    name=name,
                    symbol_kind=SymbolKind.FUNCTION,
                    signature=self._extract_signature(node, source),
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1],
                    end_col=node.end_point[1],
                    parent_name=parent_name,
                    metadata={"exported": is_export, "arrow": node_type == "arrow_function"},
                ))
                return

        if node_type in CLASS_NODES:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = self._node_text(name_node, source)
                is_export = self._is_exported(node)
                symbols.append(ParsedSymbol(
                    file_path=file_path,
                    name=name,
                    symbol_kind=SymbolKind.CLASS,
                    signature=None,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1],
                    end_col=node.end_point[1],
                    metadata={"exported": is_export},
                ))
                body = node.child_by_field_name("body")
                if body is not None:
                    for child in body.children:
                        self._walk(child, source, file_path, name, symbols)
                return

        if node_type in IFACE_NODES:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = self._node_text(name_node, source)
                symbols.append(ParsedSymbol(
                    file_path=file_path,
                    name=name,
                    symbol_kind=SymbolKind.INTERFACE,
                    signature=None,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1],
                    end_col=node.end_point[1],
                    metadata={"exported": self._is_exported(node)},
                ))

        if node_type in ENUM_NODES:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = self._node_text(name_node, source)
                symbols.append(ParsedSymbol(
                    file_path=file_path,
                    name=name,
                    symbol_kind=SymbolKind.ENUM,
                    signature=None,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1],
                    end_col=node.end_point[1],
                    metadata={"exported": self._is_exported(node)},
                ))

        if node_type in TYPE_NODES:
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = self._node_text(name_node, source)
                symbols.append(ParsedSymbol(
                    file_path=file_path,
                    name=name,
                    symbol_kind=SymbolKind.TYPE,
                    signature=None,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1],
                    end_col=node.end_point[1],
                    metadata={"exported": self._is_exported(node)},
                ))

        if node_type == "variable_declaration" or node_type == "lexical_declaration":
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    if name_node is not None:
                        name = self._node_text(name_node, source)
                        kind = SymbolKind.VARIABLE
                        if child.child_by_field_name("value") is not None:
                            val = child.child_by_field_name("value")
                            if val.type == "arrow_function":
                                kind = SymbolKind.FUNCTION
                        symbols.append(ParsedSymbol(
                            file_path=file_path,
                            name=name,
                            symbol_kind=kind,
                            signature=None,
                            start_line=child.start_point[0] + 1,
                            end_line=child.end_point[0] + 1,
                            start_col=child.start_point[1],
                            end_col=child.end_point[1],
                            parent_name=parent_name,
                            metadata={"exported": self._is_exported(node), "const": node_type == "lexical_declaration"},
                        ))

        for child in node.children:
            self._walk(child, source, file_path, parent_name, symbols)

    def _is_exported(self, node) -> bool:
        parent = node.parent
        while parent is not None:
            if parent.type == "export_statement":
                return True
            parent = parent.parent
        return False

    def _extract_signature(self, node, source: bytes) -> str | None:
        text = self._node_text(node, source)
        brace = text.find("{")
        if brace > 0:
            return text[:brace].strip()
        return text[:120]
