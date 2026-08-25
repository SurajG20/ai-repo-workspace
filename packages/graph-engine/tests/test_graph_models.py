from __future__ import annotations

from graph_engine.models import GraphRelationship, GraphSymbol, RelationshipType
from graph_engine.sync import _VERB_TO_RELATIONSHIP


def test_graph_symbol_initialization():
    sym = GraphSymbol(
        symbol_id="repo:file.ts:MyClass",
        name="MyClass",
        kind="class",
        file_path="file.ts",
        language="typescript",
        repository_id="repo",
        signature="class MyClass",
        is_exported=True,
    )
    assert sym.symbol_id == "repo:file.ts:MyClass"
    assert sym.name == "MyClass"
    assert sym.is_exported is True


def test_graph_relationship_enum():
    rel = GraphRelationship(
        source_id="r:a.py:f1",
        target_id="r:b.py:f2",
        relationship_type=RelationshipType.CALLS,
        source_file="a.py",
        target_file="b.py",
        line_number=15,
    )
    assert rel.relationship_type == RelationshipType.CALLS
    assert rel.relationship_type.value == "CALLS"


def test_verb_to_relationship_mapping():
    assert _VERB_TO_RELATIONSHIP["calls"] == RelationshipType.CALLS
    assert _VERB_TO_RELATIONSHIP["uses"] == RelationshipType.USES
    assert _VERB_TO_RELATIONSHIP["references"] == RelationshipType.USES
    assert _VERB_TO_RELATIONSHIP["extends"] == RelationshipType.EXTENDS
    assert _VERB_TO_RELATIONSHIP["implements"] == RelationshipType.IMPLEMENTS
    assert _VERB_TO_RELATIONSHIP["imports"] == RelationshipType.IMPORTS
