from __future__ import annotations

import structlog

from parser.base_extractor import BaseSymbolExtractor
from parser.models import ParsedSymbol
from shared.models.repository import SymbolKind

logger = structlog.get_logger(__name__)

_TYPE_KINDS = {"struct_specifier": SymbolKind.CLASS, "class_specifier": SymbolKind.CLASS}


class CppExtractor(BaseSymbolExtractor):
    """Symbol extractor for C and C++ (C is a strict subset of the node types)."""

    def extract(self, tree: object, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(tree.root_node, source, file_path, None, symbols)
        return symbols

    def _walk(self, node, source: bytes, file_path: str, parent_name: str | None,
              symbols: list[ParsedSymbol]) -> None:
        node_type = node.type

        if node_type == "function_definition":
            name, declared_parent = self._function_identity(
                node.child_by_field_name("declarator"), source
            )
            if name:
                is_static = self._has_storage_class(node, source, "static")
                effective_parent = parent_name or declared_parent
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.FUNCTION,
                    signature=self._extract_signature(node, source),
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    parent_name=effective_parent,
                    metadata={"exported": not is_static, "static": is_static,
                              "method": effective_parent is not None},
                ))

        elif node_type in ("struct_specifier", "class_specifier", "enum_specifier"):
            name = self._child_text(node, source, "name")
            if name:
                kind = SymbolKind.ENUM if node_type == "enum_specifier" else SymbolKind.CLASS
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=kind,
                    signature=self._node_text(node, source)[:120],
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    parent_name=parent_name,
                    metadata={"exported": True, node_type.split("_")[0]: True},
                ))
                # Methods and nested types live inside the field declaration list.
                body = node.child_by_field_name("body")
                if body:
                    for child in body.children:
                        self._walk(child, source, file_path, name, symbols)
                return

        elif node_type == "type_definition":
            name = self._typedef_name(node, source)
            if name:
                symbols.append(ParsedSymbol(
                    file_path=file_path, name=name, symbol_kind=SymbolKind.TYPE,
                    signature=None,
                    start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1], end_col=node.end_point[1],
                    parent_name=parent_name,
                    metadata={"exported": True},
                ))

        elif node_type == "declaration" and parent_name is None:
            self._extract_top_level_declaration(node, source, file_path, symbols)

        elif node_type == "field_declaration" and parent_name is not None:
            self._extract_method_prototype(node, source, file_path, parent_name, symbols)

        for child in node.children:
            child_parent = parent_name
            # Namespace definitions scope everything inside them but are not symbols.
            if node_type == "namespace_definition":
                ns_name = self._child_text(node, source, "name")
                child_parent = f"{parent_name}::{ns_name}" if parent_name else ns_name
            self._walk(child, source, file_path, child_parent, symbols)

    def _extract_method_prototype(self, node, source: bytes, file_path: str,
                                  parent_name: str, symbols: list[ParsedSymbol]) -> None:
        """Method declarations inside class/struct bodies (e.g. `void start();`)."""
        for child in node.children:
            if child.type != "function_declarator":
                continue
            name = self._declarator_name(child.child_by_field_name("declarator"), source)
            if not name:
                continue
            symbols.append(ParsedSymbol(
                file_path=file_path, name=name, symbol_kind=SymbolKind.FUNCTION,
                signature=self._node_text(node, source)[:120],
                start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
                start_col=node.start_point[1], end_col=node.end_point[1],
                parent_name=parent_name,
                metadata={"exported": True, "method": True, "declaration": True},
            ))

    def _extract_top_level_declaration(self, node, source: bytes, file_path: str,
                                       symbols: list[ParsedSymbol]) -> None:
        """Global/namespace-scope variable declarations (e.g. globals, statics)."""
        declarator = node.child_by_field_name("declarator")
        if declarator is None:
            return
        name = self._declarator_name(declarator, source)
        if not name or "(" in self._node_text(declarator, source):
            return  # function prototypes add noise; skip them
        is_static = self._has_storage_class(node, source, "static")
        is_const = self._has_type_qualifier(node, source)
        symbols.append(ParsedSymbol(
            file_path=file_path, name=name, symbol_kind=SymbolKind.VARIABLE,
            signature=None,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            start_col=node.start_point[1], end_col=node.end_point[1],
            metadata={"exported": not is_static, "static": is_static, "const": is_const},
        ))

    def _declarator_name(self, declarator, source: bytes) -> str | None:
        """Dig through pointer/array/function declarators to the identifier."""
        while declarator is not None:
            if declarator.type in ("identifier", "field_identifier", "type_identifier"):
                return self._node_text(declarator, source)
            if declarator.type == "qualified_identifier":
                return self._node_text(declarator, source)
            field_declarator = declarator.child_by_field_name("declarator")
            if field_declarator is None:
                return None
            declarator = field_declarator
        return None

    def _function_identity(self, declarator, source: bytes) -> tuple[str | None, str | None]:
        """Return (function_name, owner) splitting qualified names like Engine::start."""
        raw = self._declarator_name(declarator, source)
        if raw is None:
            return None, None
        if "::" in raw:
            owner, _, name = raw.rpartition("::")
            return name, owner
        return raw, None

    def _typedef_name(self, node, source: bytes) -> str | None:
        declarator = node.child_by_field_name("declarator")
        if declarator is None:
            return None
        if declarator.type == "type_identifier":
            return self._node_text(declarator, source)
        return self._declarator_name(declarator, source)

    def _has_storage_class(self, node, source: bytes, keyword: str) -> bool:
        return any(
            child.type == "storage_class_specifier"
            and self._node_text(child, source) == keyword
            for child in node.children
        )

    def _has_type_qualifier(self, node, source: bytes) -> bool:
        type_node = node.child_by_field_name("type")
        if type_node is None:
            return False
        return any(
            child.type == "type_qualifier" and self._node_text(child, source) == "const"
            for child in type_node.children
        ) or (type_node.type == "primitive_type"
              and self._node_text(type_node, source).startswith("const"))

    def _extract_signature(self, node, source: bytes) -> str | None:
        text = self._node_text(node, source)
        brace = text.find("{")
        if brace > 0:
            return " ".join(text[:brace].split())
        return text[:120]
