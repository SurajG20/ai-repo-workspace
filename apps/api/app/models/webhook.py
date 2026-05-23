from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.repository import EventType, ProviderType

from .base import Base, TimestampMixin, new_uuid


class WebhookEvent(Base, TimestampMixin):
    __tablename__ = "webhook_events"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    provider: Mapped[ProviderType] = mapped_column(String(32), nullable=False)
    event_type: Mapped[EventType] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128))
    signature_valid: Mapped[Optional[bool]] = mapped_column(Boolean)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payload_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processing_job_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    replay_count: Mapped[int] = mapped_column(default=0)
    last_replayed_at: Mapped[Optional[str]] = mapped_column()
    processed_at: Mapped[Optional[str]] = mapped_column()

    repository: Mapped["Repository"] = relationship(back_populates="webhook_events")
