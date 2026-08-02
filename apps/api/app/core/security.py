from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import JWTError, jwt

from ..config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def _get_fernet() -> Fernet:
    key = hashlib.sha256(settings.api_secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, settings.api_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        return user_id
    except JWTError:
        return None


def encrypt_token(token: str) -> bytes:
    f = _get_fernet()
    return f.encrypt(token.encode("utf-8"))


def decrypt_token(encrypted: bytes) -> str | None:
    try:
        f = _get_fernet()
        return f.decrypt(encrypted).decode("utf-8")
    except Exception:
        return None
