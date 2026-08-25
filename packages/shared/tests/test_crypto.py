from __future__ import annotations

import pytest
from shared.crypto import decrypt_secret, encrypt_secret, fernet_for
from shared.models.symbol import IndexedSymbol, SymbolRelationship, build_symbol_id


def test_fernet_derivation_deterministic():
    f1 = fernet_for("my-secret-key")
    f2 = fernet_for("my-secret-key")
    ciphertext = f1.encrypt(b"hello world")
    assert f2.decrypt(ciphertext) == b"hello world"


def test_encrypt_decrypt_secret_roundtrip():
    secret = "production-app-secret-12345"
    token = "ghp_AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
    encrypted = encrypt_secret(secret, token)
    assert isinstance(encrypted, bytes)
    assert encrypted != token.encode()

    decrypted = decrypt_secret(secret, encrypted)
    assert decrypted == token


def test_decrypt_secret_invalid_key_returns_none():
    secret1 = "secret-1"
    secret2 = "secret-2"
    encrypted = encrypt_secret(secret1, "sensitive_data")
    assert decrypt_secret(secret2, encrypted) is None


def test_build_symbol_id():
    assert build_symbol_id("repo-123", "src/auth/login.py", "create_token") == "repo-123:src/auth/login.py:create_token"


def test_indexed_symbol_payload_serialization():
    sym = IndexedSymbol(
        symbol_id="r1:a.py:foo",
        repository_id="r1",
        snapshot_id="s1",
        name="foo",
        kind="function",
        file_path="a.py",
        signature="def foo(x: int) -> str",
        start_line=1,
        end_line=5,
        start_col=0,
        end_col=10,
        parent_name=None,
        is_exported=True,
        extras={"docstring": "helper"},
    )
    payload = sym.to_payload()
    assert payload["symbol_id"] == "r1:a.py:foo"
    assert payload["is_exported"] is True
    assert payload["extras"] == {"docstring": "helper"}

    restored = IndexedSymbol.from_payload(payload)
    assert restored == sym


def test_symbol_relationship_payload_serialization():
    rel = SymbolRelationship(
        relationship_id="rel-1",
        repository_id="r1",
        snapshot_id="s1",
        source_symbol_id="r1:a.py:caller",
        target_symbol_id="r1:b.py:callee",
        source_file="a.py",
        source_symbol="caller",
        target_symbol="callee",
        relationship_type="calls",
        target_file="b.py",
        resolved_file="b.py",
        line_number=42,
        extras={"async": True},
    )
    payload = rel.to_payload()
    assert payload["relationship_id"] == "rel-1"
    assert payload["relationship_type"] == "calls"

    restored = SymbolRelationship.from_payload(payload)
    assert restored == rel
