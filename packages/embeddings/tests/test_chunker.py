from __future__ import annotations

from embeddings.chunker import chunk_from_symbol, chunk_module, chunk_symbol
from shared.models.symbol import IndexedSymbol


def test_chunk_symbol_function():
    chunk = chunk_symbol(
        symbol_name="create_access_token",
        kind="function",
        signature="def create_access_token(user_id: str) -> str",
        file_path="apps/api/app/core/security.py",
        parent_name=None,
    )
    assert "[FUNCTION] create_access_token" in chunk
    assert "def create_access_token" in chunk
    assert "@ apps/api/app/core/security.py" in chunk


def test_chunk_symbol_with_parent_class():
    chunk = chunk_symbol(
        symbol_name="authenticate",
        kind="method",
        signature="async def authenticate(self) -> bool",
        file_path="services/auth.py",
        parent_name="AuthService",
    )
    assert "[METHOD] authenticate:AuthService" in chunk
    assert "@ services/auth.py" in chunk


def test_chunk_from_indexed_symbol():
    sym = IndexedSymbol(
        symbol_id="repo:path.py:foo",
        repository_id="repo",
        snapshot_id=None,
        name="foo",
        kind="function",
        file_path="path.py",
        signature="def foo(): pass",
    )
    chunk = chunk_from_symbol(sym)
    assert "[FUNCTION] foo" in chunk
    assert "def foo(): pass" in chunk
    assert "@ path.py" in chunk


def test_chunk_module():
    chunk = chunk_module("utils.py", "python", ["clean", "format", "validate"])
    assert "[MODULE] utils.py" in chunk
    assert "Language: python" in chunk
    assert "Symbols: clean, format, validate" in chunk
