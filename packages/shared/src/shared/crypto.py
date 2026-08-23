from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


def fernet_for(secret: str) -> Fernet:
    """Derive a Fernet from an app secret.

    Both the api (encrypting provider tokens at login) and the workers
    (decrypting them when a stage runs) must derive the same key.
    """
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_secret(secret: str, plaintext: str) -> bytes:
    return fernet_for(secret).encrypt(plaintext.encode("utf-8"))


def decrypt_secret(secret: str, encrypted: bytes) -> str | None:
    try:
        return fernet_for(secret).decrypt(encrypted).decode("utf-8")
    except Exception:
        return None
