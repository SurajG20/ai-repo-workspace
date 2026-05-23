from __future__ import annotations

import structlog

from parser.base_dependency import BaseDependencyExtractor
from parser.models import SymbolRelationship

logger = structlog.get_logger(__name__)


class GoDependencyExtractor(BaseDependencyExtractor):
    def extract(self, tree, source: bytes, file_path: str, symbols: list) -> list[SymbolRelationship]:
        relationships: list[SymbolRelationship] = []
        self._walk(tree.root_node, source, file_path, relationships)
        return relationships

    def _walk(self, node, source: bytes, file_path: str, relationships: list[SymbolRelationship]):
        if node.type == "import_declaration":
            for child in node.children:
                if child.type == "import_spec":
                    path_node = child.child_by_field_name("path")
                    if path_node:
                        module = self._node_text(path_node, source).strip('"')
                        alias = module.split("/")[-1]
                        name_node = child.child_by_field_name("name")
                        if name_node:
                            alias = self._node_text(name_node, source)
                        relationships.append(SymbolRelationship(
                            source_file=file_path,
                            source_symbol=alias,
                            target_symbol=module.split("/")[-1],
                            relationship_type="imports",
                            target_file=module,
                            line_number=child.start_point[0] + 1,
                            metadata={"module": module},
                        ))

        if node.type == "call_expression":
            func = node.child_by_field_name("function")
            if func:
                name = self._extract_call_name(func, source)
                if name:
                    relationships.append(SymbolRelationship(
                        source_file=file_path,
                        source_symbol=name,
                        target_symbol=name,
                        relationship_type="calls",
                        line_number=node.start_point[0] + 1,
                    ))

        for child in node.children:
            self._walk(child, source, file_path, relationships)

    def _extract_call_name(self, node, source: bytes) -> str | None:
        if node.type == "identifier":
            return self._node_text(node, source)
        if node.type == "selector_expression":
            operand = node.child_by_field_name("operand")
            field = node.child_by_field_name("field")
            if operand and field:
                return f"{self._node_text(operand, source)}.{self._node_text(field, source)}"
        return None
