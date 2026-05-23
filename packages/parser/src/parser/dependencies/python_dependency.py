from __future__ import annotations

import structlog

from parser.base_dependency import BaseDependencyExtractor
from parser.models import SymbolRelationship

logger = structlog.get_logger(__name__)


class PythonDependencyExtractor(BaseDependencyExtractor):
    def extract(self, tree, source: bytes, file_path: str, symbols: list) -> list[SymbolRelationship]:
        relationships: list[SymbolRelationship] = []
        symbol_names = {s.name for s in symbols}
        self._walk(tree.root_node, source, file_path, symbol_names, relationships)
        return relationships

    def _walk(self, node, source: bytes, file_path: str, symbol_names: set[str], relationships: list[SymbolRelationship]):
        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name":
                    module = self._node_text(child, source)
                    relationships.append(SymbolRelationship(
                        source_file=file_path,
                        source_symbol=module.split(".")[0],
                        target_symbol=module,
                        relationship_type="imports",
                        target_file=module.replace(".", "/"),
                        line_number=node.start_point[0] + 1,
                        metadata={"module": module, "kind": "import"},
                    ))
                elif child.type == "aliased_import":
                    name = self._node_text(child, source).split(" as ")[-1].strip()
                    relationships.append(SymbolRelationship(
                        source_file=file_path,
                        source_symbol=name,
                        target_symbol=name,
                        relationship_type="imports",
                        line_number=node.start_point[0] + 1,
                        metadata={"kind": "aliased"},
                    ))
            return

        if node.type == "import_from_statement":
            module_name = None
            names = []
            for child in node.children:
                if child.type == "dotted_name":
                    module_name = self._node_text(child, source)
                elif child.type == "dotted_name" or child.type == "aliased_import":
                    t = self._node_text(child, source).split(" as ")[-1].strip()
                    names.append(t)
                elif child.type == "identifier":
                    names.append(self._node_text(child, source))
            for n in names:
                relationships.append(SymbolRelationship(
                    source_file=file_path,
                    source_symbol=n,
                    target_symbol=f"{module_name}.{n}" if module_name else n,
                    relationship_type="imports",
                    target_file=module_name.replace(".", "/") if module_name else None,
                    line_number=node.start_point[0] + 1,
                    metadata={"module": module_name, "kind": "from"},
                ))
            return

        if node.type == "call":
            func = node.child_by_field_name("function")
            if func:
                caller_name = self._extract_call_name(func, source)
                if caller_name:
                    relationships.append(SymbolRelationship(
                        source_file=file_path,
                        source_symbol=caller_name,
                        target_symbol=caller_name,
                        relationship_type="calls",
                        line_number=node.start_point[0] + 1,
                    ))

        for child in node.children:
            self._walk(child, source, file_path, symbol_names, relationships)

    def _extract_call_name(self, node, source: bytes) -> str | None:
        if node.type == "identifier":
            return self._node_text(node, source)
        if node.type == "attribute":
            obj = node.child_by_field_name("object")
            attr = node.child_by_field_name("attribute")
            if obj and attr:
                return f"{self._node_text(obj, source)}.{self._node_text(attr, source)}"
        return None
