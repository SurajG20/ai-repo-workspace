from __future__ import annotations

import structlog

from parser.base_dependency import BaseDependencyExtractor
from parser.models import SymbolRelationship

logger = structlog.get_logger(__name__)

METHOD_CALL_PATTERNS = ("call_expression", "new_expression")


class TypeScriptDependencyExtractor(BaseDependencyExtractor):
    def extract(self, tree, source: bytes, file_path: str, symbols: list) -> list[SymbolRelationship]:
        relationships: list[SymbolRelationship] = []
        symbol_names = {s.name for s in symbols}
        self._walk(tree.root_node, source, file_path, symbol_names, relationships)
        return relationships

    def _walk(self, node, source: bytes, file_path: str, symbol_names: set[str], relationships: list[SymbolRelationship]):
        if node.type == "import_statement":
            source_clause = node.child_by_field_name("source")
            if source_clause:
                module_spec = self._node_text(source_clause, source).strip("'\"")
                spec_node = node.child_by_field_name("specifier")
                if spec_node:
                    for child in node.children:
                        if child.type == "import_specifier":
                            import_name = self._node_text(child.child_by_field_name("name"), source)
                            relationships.append(SymbolRelationship(
                                source_file=file_path,
                                source_symbol=import_name,
                                target_symbol=import_name,
                                relationship_type="imports",
                                target_file=module_spec,
                                line_number=child.start_point[0] + 1,
                                metadata={"module": module_spec, "kind": "named"},
                            ))
                        elif child.type == "namespace_import":
                            alias = self._node_text(child.child_by_field_name("alias"), source)
                            relationships.append(SymbolRelationship(
                                source_file=file_path,
                                source_symbol=alias,
                                target_symbol="*",
                                relationship_type="imports",
                                target_file=module_spec,
                                line_number=child.start_point[0] + 1,
                                metadata={"module": module_spec, "kind": "namespace"},
                            ))
            return

        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node:
                if func_node.type == "identifier":
                    name = self._node_text(func_node, source)
                    if name in symbol_names or True:
                        relationships.append(SymbolRelationship(
                            source_file=file_path,
                            source_symbol=name,
                            target_symbol=name,
                            relationship_type="calls",
                            line_number=func_node.start_point[0] + 1,
                        ))
                elif func_node.type == "member_expression":
                    obj = func_node.child_by_field_name("object")
                    if obj:
                        obj_name = self._node_text(obj, source)
                        relationships.append(SymbolRelationship(
                            source_file=file_path,
                            source_symbol=obj_name,
                            target_symbol=self._node_text(func_node, source),
                            relationship_type="references",
                            line_number=func_node.start_point[0] + 1,
                        ))

        if node.type == "new_expression":
            ctor = node.child_by_field_name("constructor")
            if ctor and ctor.type == "identifier":
                name = self._node_text(ctor, source)
                relationships.append(SymbolRelationship(
                    source_file=file_path,
                    source_symbol=name,
                    target_symbol=name,
                    relationship_type="instantiates",
                    line_number=ctor.start_point[0] + 1,
                ))

        for child in node.children:
            self._walk(child, source, file_path, symbol_names, relationships)
