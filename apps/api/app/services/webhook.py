from __future__ import annotations

import hashlib
import hmac
import uuid

import structlog
from shared.models.repository import EventType, ProviderType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.repository import Repository
from ..models.webhook import WebhookEvent

logger = structlog.get_logger(__name__)

GITHUB_SIGNATURE_PREFIX = "sha256="


def _verify_github_signature(payload: bytes, signature_header: str | None, secret: str) -> bool:
    if not signature_header or not signature_header.startswith(GITHUB_SIGNATURE_PREFIX):
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    provided = signature_header[len(GITHUB_SIGNATURE_PREFIX):]
    return hmac.compare_digest(expected, provided)


class WebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _resolve_repository_id(self, payload: dict) -> uuid.UUID | None:
        repo_full_name = payload.get("repository", {}).get("full_name")
        if not repo_full_name:
            return None
        stmt = select(Repository.id).where(
            Repository.full_name == repo_full_name,
            Repository.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def handle_github_event(
        self,
        event_type: str,
        delivery_id: str | None,
        payload: dict,
        signature: str | None,
        raw_body: bytes | None = None,
    ) -> WebhookEvent:
        event_type_enum = _map_github_event(event_type)
        repo_full_name = payload.get("repository", {}).get("full_name", "unknown")

        signature_valid = None
        webhook_secret = settings.github_webhook_secret or settings.api_secret_key[:32]
        if raw_body is not None and webhook_secret:
            signature_valid = _verify_github_signature(
                raw_body, signature, webhook_secret
            )
            if not signature_valid:
                logger.warning(
                    "webhook_invalid_signature",
                    delivery=delivery_id,
                    repo=repo_full_name,
                )

        repository_id = await self._resolve_repository_id(payload)
        if not repository_id:
            repository_id = uuid.uuid4()
            logger.warning(
                "webhook_unresolved_repo",
                repo=repo_full_name,
                assigned_fake_id=str(repository_id),
            )

        if delivery_id:
            stmt = select(WebhookEvent).where(
                WebhookEvent.idempotency_key == delivery_id,
                WebhookEvent.provider == ProviderType.GITHUB,
            )
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none():
                logger.info("duplicate_webhook", delivery_id=delivery_id)
                event = WebhookEvent(
                    repository_id=repository_id,
                    provider=ProviderType.GITHUB,
                    event_type=event_type_enum,
                    idempotency_key=delivery_id,
                    signature_valid=signature_valid,
                    payload=payload,
                    payload_size_bytes=len(str(payload).encode()),
                    processed=True,
                )
                self.session.add(event)
                await self.session.flush()
                return event

        event = WebhookEvent(
            repository_id=repository_id,
            provider=ProviderType.GITHUB,
            event_type=event_type_enum,
            idempotency_key=delivery_id,
            signature_valid=signature_valid,
            payload=payload,
            payload_size_bytes=len(str(payload).encode()),
            processed=False,
        )
        self.session.add(event)
        await self.session.flush()
        logger.info("webhook_received", event_type=event_type_enum, repo=repo_full_name)
        return event


def _map_github_event(event_type: str) -> EventType:
    mapping = {
        "push": EventType.PUSH,
        "pull_request": EventType.PULL_REQUEST,
        "pull_request_review": EventType.PULL_REQUEST_REVIEW,
        "create": EventType.CREATE,
        "delete": EventType.DELETE,
        "repository": EventType.REPOSITORY,
    }
    return mapping.get(event_type, EventType.PUSH)
