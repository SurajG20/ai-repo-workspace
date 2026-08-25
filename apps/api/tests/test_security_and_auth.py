from __future__ import annotations

import hashlib
import hmac
import uuid

import pytest
from app.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    decrypt_token,
    encrypt_token,
)
from app.services.webhook import _verify_github_signature


def test_jwt_create_and_decode():
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded == user_id


def test_jwt_decode_invalid():
    assert decode_access_token("invalid.token.structure") is None
    assert decode_access_token("") is None


def test_encrypt_and_decrypt_token():
    plain = "ghp_secretaccesstoken12345"
    encrypted = encrypt_token(plain)
    assert isinstance(encrypted, bytes)
    assert encrypted != plain.encode()

    decrypted = decrypt_token(encrypted)
    assert decrypted == plain


def test_webhook_hmac_signature_verification():
    secret = "my-webhook-secret-key"
    payload = b'{"action": "push", "repository": {"full_name": "org/repo"}}'

    mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    valid_header = f"sha256={mac}"

    assert _verify_github_signature(payload, valid_header, secret) is True
    assert _verify_github_signature(payload, "sha256=invalid_hash", secret) is False
    assert _verify_github_signature(payload, "invalid_format", secret) is False
    assert _verify_github_signature(payload, None, secret) is False
