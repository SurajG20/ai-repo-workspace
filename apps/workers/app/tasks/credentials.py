"""Credential resolution for pipeline stages.

Secrets never ride in the Job envelope: the clone executor resolves the
repository owner's stored (encrypted) GitHub token at execution time,
behind this module's seam.
"""

from __future__ import annotations

import uuid

import asyncpg
import structlog
from shared.crypto import decrypt_secret

from ..config import settings

logger = structlog.get_logger(__name__)


async def resolve_user_github_token(pool: asyncpg.Pool, owner_id: str | None) -> str:
    """Decrypt the owner's stored GitHub token; empty string when absent."""
    if not owner_id:
        return ""
    try:
        owner = uuid.UUID(owner_id)
    except ValueError:
        return ""

    row = await pool.fetchrow(
        "SELECT access_token FROM users WHERE id = $1", owner
    )
    token_bytes = row["access_token"] if row else None
    if not token_bytes:
        return ""

    token = decrypt_secret(settings.api_secret_key, token_bytes)
    if token is None:
        logger.warning("credential_decrypt_failed", owner=str(owner))
        return ""
    return token
