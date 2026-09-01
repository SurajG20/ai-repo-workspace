from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..services.webhook import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = structlog.get_logger(__name__)


@router.post("/github")
async def github_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    event_type = request.headers.get("X-GitHub-Event", "push")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    signature = request.headers.get("X-Hub-Signature-256")
    raw_body = await request.body()
    payload = await request.json()

    service = WebhookService(session)
    await service.handle_github_event(
        event_type, delivery_id, payload, signature, raw_body=raw_body
    )
    await session.commit()

    logger.info("webhook_processed", event=event_type, delivery=delivery_id)
    return {"status": "received"}
