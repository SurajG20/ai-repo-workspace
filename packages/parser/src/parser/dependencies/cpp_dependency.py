from __future__ import annotations

import structlog

from parser.base_dependency import BaseDependencyExtractor
from parser.models import SymbolRelationship

logger = structlog.get_logger(__name__)


class CppDependencyExtractor(BaseDependencyExtractor):
    """Extracts #include directives as module-import relationships.

    System includes (<...>) are skipped; only quoted includes that resolve to
    files inside the repository produce relationships.
    """

    def extract(
        self,
        tree: object,
        source: bytes,
        file_path: str,
        symbols,
    ) -> list[SymbolRelationship]:
        relationships: list[SymbolRelationship] = []
        self._walk(tree.root_node, source, file_path, relationships)
        return relationships

    def _walk(self, node, source: bytes, file_path: str,
              relationships: list[SymbolRelationship]) -> None:
        if node.type == "preproc_include":
            path_node = node.child_by_field_name("path")
            if path_node is not None:
                include = self._node_text(path_node, source).strip('"')
                if not include.startswith("<"):
                    relationships.append(SymbolRelationship(
                        source_file=file_path,
                        source_symbol=include,
                        target_symbol=include,
                        relationship_type="imports_module",
                        line_number=node.start_point[0] + 1,
                        metadata={"specifier": include},
                    ))
        for child in node.children:
            self._walk(child, source, file_path, relationships)
