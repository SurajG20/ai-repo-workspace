from __future__ import annotations

import structlog

from parser.base_dependency import BaseDependencyExtractor
from parser.models import SymbolRelationship

logger = structlog.get_logger(__name__)


class RustDependencyExtractor(BaseDependencyExtractor):
    def extract(self, tree, source: bytes, file_path: str, symbols: list) -> list[SymbolRelationship]:
        relationships: list[SymbolRelationship] = []
        self._walk(tree.root_node, source, file_path, relationships)
        return relationships

    def _walk(self, node, source: bytes, file_path: str, relationships: list[SymbolRelationship]):
        if node.type == "use_declaration":
            path = self._extract_use_path(node, source)
            if path:
                relationships.append(SymbolRelationship(
                    source_file=file_path,
                    source_symbol=path.split("::")[-1],
                    target_symbol=path,
                    relationship_type="imports",
                    target_file=path.replace("::", "/"),
                    line_number=node.start_point[0] + 1,
                    metadata={"module": path, "kind": "use"},
                ))

        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func:
                name = self._extract_call_name(func, source)
                if name:
                    relationships.append(SymbolRelationship(
                        source_file=file_path,
                        source_symbol=name.split("::")[-1],
                        target_symbol=name,
                        relationship_type="calls",
                        line_number=node.start_point[0] + 1,
                    ))

        for child in node.children:
            self._walk(child, source, file_path, relationships)

    def _extract_use_path(self, node, source: bytes) -> str | None:
        for child in node.children:
            if child.type in ("scoped_identifier", "identifier", "scoped_use_list"):
                return self._node_text(child, source)
        return None

    def _extract_call_name(self, node, source: bytes) -> str | None:
        if node.type == "identifier":
            return self._node_text(node, source)
        if node.type in ("scoped_identifier", "field_expression"):
            return self._node_text(node, source)
        return None
