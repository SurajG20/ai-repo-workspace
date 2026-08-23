from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from shared.crypto import decrypt_secret, encrypt_secret

from ..config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def create_access_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
    return encrypt_secret(settings.api_secret_key, token)


def decrypt_token(encrypted: bytes) -> str | None:
    return decrypt_secret(settings.api_secret_key, encrypted)
