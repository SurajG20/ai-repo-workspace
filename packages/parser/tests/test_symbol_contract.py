from __future__ import annotations

from parser import (
    ParsedSymbol,
    SymbolRelationship,
    build_symbol_id,
    derive_is_exported,
    to_indexed_relationship,
    to_indexed_symbol,
)
from shared.models.repository import SymbolKind
from shared.models.symbol import IndexedSymbol, SymbolRelationship as SharedRelationship


def make_symbol(name="handler", **kwargs) -> ParsedSymbol:
    return ParsedSymbol(
        file_path=kwargs.pop("file_path", "src/app.ts"),
        name=name,
        symbol_kind=kwargs.pop("symbol_kind", SymbolKind.FUNCTION),
        **kwargs,
    )


def test_build_symbol_id_is_stable_and_shared():
    assert build_symbol_id("repo-1", "src/app.ts", "handler") == "repo-1:src/app.ts:handler"


def test_to_indexed_symbol_maps_every_field():
    parsed = make_symbol(
        signature="function handler(): void",
        start_line=10,
        end_line=20,
        start_col=2,
        end_col=4,
        parent_name=None,
        metadata={"exported": True, "arrow": False},
    )
    record = to_indexed_symbol(parsed, repository_id="repo-1", snapshot_id="snap-1")

    assert record.symbol_id == "repo-1:src/app.ts:handler"
    assert record.repository_id == "repo-1"
    assert record.snapshot_id == "snap-1"
    assert record.name == "handler"
    assert record.kind == "function"
    assert record.is_exported is True
    assert record.extras["arrow"] is False

    payload = record.to_payload()
    restored = IndexedSymbol.from_payload(payload)
    assert restored == record


def test_regression_metadata_exported_flag_becomes_is_exported():
    # The old bug: sync read metadata["is_exported"] while extractors wrote
    # metadata["exported"], so every symbol landed in Neo4j unexported.
    parsed = make_symbol(metadata={"exported": True})
    derived = derive_is_exported(parsed, "typescript")
    assert derived is True
    record = to_indexed_symbol(
        parsed, repository_id="r", snapshot_id=None, language="typescript"
    )
    assert record.is_exported is True


def test_derive_is_exported_per_language():
    ts = make_symbol(metadata={"exported": True})
    assert derive_is_exported(ts, "typescript") is True
    assert derive_is_exported(ts, "javascript") is True

    go = make_symbol(name="Server", metadata={"exported": True})
    assert derive_is_exported(go, "go") is True

    rust = make_symbol(metadata={"public": True})
    assert derive_is_exported(rust, "rust") is True

    java_public = make_symbol(metadata={"visibility": "public"})
    assert derive_is_exported(java_public, "java") is True
    java_private = make_symbol(metadata={"visibility": "private"})
    assert derive_is_exported(java_private, "java") is False

    py_public = make_symbol(name="run_pipeline")
    assert derive_is_exported(py_public, "python") is True
    py_private = make_symbol(name="_run_pipeline")
    assert derive_is_exported(py_private, "python") is False

    unknown = make_symbol()
    assert derive_is_exported(unknown, "cobol") is False


def test_python_underscore_heuristic():
    assert derive_is_exported(make_symbol(name="helper"), "python") is True
    assert derive_is_exported(make_symbol(name="_helper"), "python") is False


def test_to_indexed_relationship_falls_back_to_name_based_ids():
    rel = SymbolRelationship(
        source_file="src/a.ts",
        source_symbol="caller",
        target_symbol="callee",
        relationship_type="calls",
    )
    record = to_indexed_relationship(
        rel,
        repository_id="repo-1",
        snapshot_id="snap-1",
        resolved_target_file="src/b.ts",
    )

    assert record.relationship_id
    assert record.source_symbol_id == "repo-1:src/a.ts:caller"
    assert record.target_symbol_id == "repo-1:src/b.ts:callee"
    assert record.resolved_file == "src/b.ts"

    restored = SharedRelationship.from_payload(record.to_payload())
    assert restored == record
