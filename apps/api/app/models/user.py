from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.repository import ProviderType

from .base import Base, SoftDeleteMixin, TimestampUpdateMixin, new_uuid, utcnow


class User(Base, TimestampUpdateMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    provider: Mapped[ProviderType] = mapped_column(default=ProviderType.GITHUB)
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    login: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    access_token: Mapped[Optional[bytes]] = mapped_column(BYTEA)
    token_expires: Mapped[Optional[datetime]] = mapped_column()
    refresh_token: Mapped[Optional[bytes]] = mapped_column(BYTEA)
    last_login_at: Mapped[datetime] = mapped_column(default=utcnow)

    repositories: Mapped[list["Repository"]] = relationship(back_populates="owner")
