from __future__ import annotations

import structlog
from shared.models.repository import SymbolKind

from parser.base_extractor import BaseSymbolExtractor
from parser.models import ParsedSymbol

logger = structlog.get_logger(__name__)


class PythonExtractor(BaseSymbolExtractor):
    def extract(self, tree: object, source: bytes, file_path: str) -> list[ParsedSymbol]:
        symbols: list[ParsedSymbol] = []
        self._walk(tree.root_node, source, file_path, None, symbols)
        return symbols

    def _walk(self, node, source: bytes, file_path: str, parent_name: str | None, symbols: list[ParsedSymbol]):
        node_type = node.type

        if node_type == "function_definition":
            name = self._child_text(node, source, "name")
            if name:
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
                    metadata={"decorators": self._extract_decorators(node, source)},
                ))

        if node_type == "class_definition":
            name = self._child_text(node, source, "name")
            if name:
                bases = self._extract_bases(node, source)
                symbols.append(ParsedSymbol(
                    file_path=file_path,
                    name=name,
                    symbol_kind=SymbolKind.CLASS,
                    signature=None,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    start_col=node.start_point[1],
                    end_col=node.end_point[1],
                    metadata={"bases": bases, "decorators": self._extract_decorators(node, source)},
                ))
                body = node.child_by_field_name("body")
                if body is not None:
                    for child in body.children:
                        self._walk(child, source, file_path, name, symbols)
                return

        if node_type == "assignment":
            for child in node.children:
                if child.type == "identifier":
                    name = self._node_text(child, source)
                    if parent_name is None:
                        symbols.append(ParsedSymbol(
                            file_path=file_path,
                            name=name,
                            symbol_kind=SymbolKind.VARIABLE,
                            signature=None,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            start_col=node.start_point[1],
                            end_col=node.end_point[1],
                            parent_name=parent_name,
                        ))

        for child in node.children:
            self._walk(child, source, file_path, parent_name, symbols)

    def _extract_signature(self, node, source: bytes) -> str | None:
        params = node.child_by_field_name("parameters")
        if params:
            return self._node_text(params, source)
        return None

    def _extract_decorators(self, node, source: bytes) -> list[str]:
        decs = []
        for child in node.children:
            if child.type == "decorator":
                decs.append(self._node_text(child, source))
        return decs

    def _extract_bases(self, node, source: bytes) -> list[str]:
        bases = []
        for child in node.children:
            if child.type == "argument_list":
                for arg in child.children:
                    if arg.type == "identifier":
                        bases.append(self._node_text(arg, source))
        return bases
