from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from shared.models.repository import ProviderType
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import BYTEA, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampUpdateMixin, new_uuid, utcnow

if TYPE_CHECKING:
    from .repository import Repository


class User(Base, TimestampUpdateMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    provider: Mapped[ProviderType] = mapped_column(String(32), default=ProviderType.GITHUB)
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    login: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[bytes | None] = mapped_column(BYTEA)
    token_expires: Mapped[datetime | None] = mapped_column()
    refresh_token: Mapped[bytes | None] = mapped_column(BYTEA)
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    repositories: Mapped[list[Repository]] = relationship(back_populates="owner")
