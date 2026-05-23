from __future__ import annotations

import structlog

from parser.base_dependency import BaseDependencyExtractor
from parser.models import SymbolRelationship

logger = structlog.get_logger(__name__)


class JavaDependencyExtractor(BaseDependencyExtractor):
    def extract(self, tree, source: bytes, file_path: str, symbols: list) -> list[SymbolRelationship]:
        relationships: list[SymbolRelationship] = []
        self._walk(tree.root_node, source, file_path, relationships)
        return relationships

    def _walk(self, node, source: bytes, file_path: str, relationships: list[SymbolRelationship]):
        if node.type == "import_declaration":
            for child in node.children:
                if child.type in ("identifier", "scoped_identifier"):
                    module = self._node_text(child, source)
                    parts = module.split(".")
                    relationships.append(SymbolRelationship(
                        source_file=file_path,
                        source_symbol=parts[-1],
                        target_symbol=module,
                        relationship_type="imports",
                        target_file=module.replace(".", "/"),
                        line_number=node.start_point[0] + 1,
                        metadata={"module": module},
                    ))
                    break

        if node.type == "method_invocation":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = self._node_text(name_node, source)
                relationships.append(SymbolRelationship(
                    source_file=file_path,
                    source_symbol=name,
                    target_symbol=name,
                    relationship_type="calls",
                    line_number=node.start_point[0] + 1,
                ))

        if node.type == "object_creation_expression":
            type_node = node.child_by_field_name("type")
            if type_node:
                name = self._node_text(type_node, source)
                relationships.append(SymbolRelationship(
                    source_file=file_path,
                    source_symbol=name,
                    target_symbol=name,
                    relationship_type="instantiates",
                    line_number=node.start_point[0] + 1,
                ))

        for child in node.children:
            self._walk(child, source, file_path, relationships)
