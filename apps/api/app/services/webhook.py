from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.repository import EventType, ProviderType

from ..models.webhook import WebhookEvent

logger = structlog.get_logger(__name__)


class WebhookService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def handle_github_event(
        self,
        event_type: str,
        delivery_id: str | None,
        payload: dict,
        signature: str | None,
    ) -> WebhookEvent:
        event_type_enum = _map_github_event(event_type)
        repo_full_name = payload.get("repository", {}).get("full_name", "unknown")

        event = WebhookEvent(
            repository_id=uuid.uuid4(),
            provider=ProviderType.GITHUB,
            event_type=event_type_enum,
            idempotency_key=delivery_id,
            signature_valid=None,
            payload=payload,
            payload_size_bytes=len(str(payload).encode()),
            processed=False,
        )

        if delivery_id:
            from sqlalchemy import select
            stmt = select(WebhookEvent).where(
                WebhookEvent.idempotency_key == delivery_id,
                WebhookEvent.provider == ProviderType.GITHUB,
            )
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none():
                logger.info("duplicate_webhook", delivery_id=delivery_id)
                event.processed = True
                self.session.add(event)
                await self.session.flush()
                return event

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
