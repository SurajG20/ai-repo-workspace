from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from shared.models.repository import ProviderType, RepositoryStatus
from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin, TimestampUpdateMixin, new_uuid

if TYPE_CHECKING:
    from .file import RepositoryFile
    from .job import IndexingJob
    from .snapshot import RepositorySnapshot
    from .user import User
    from .webhook import WebhookEvent


class Repository(Base, TimestampUpdateMixin, SoftDeleteMixin):
    __tablename__ = "repositories"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    owner_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider: Mapped[ProviderType] = mapped_column(String(32), default=ProviderType.GITHUB)
    provider_id: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(512), nullable=False)
    clone_url: Mapped[str | None] = mapped_column(Text)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    language: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[RepositoryStatus] = mapped_column(String(32), default=RepositoryStatus.PENDING)
    last_synced_at: Mapped[datetime | None] = mapped_column()
    last_synced_sha: Mapped[str | None] = mapped_column(String(40))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    owner: Mapped[User] = relationship(back_populates="repositories")
    languages: Mapped[list[RepositoryLanguage]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    snapshots: Mapped[list[RepositorySnapshot]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    files: Mapped[list[RepositoryFile]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    jobs: Mapped[list[IndexingJob]] = relationship(back_populates="repository", cascade="all, delete-orphan")
    webhook_events: Mapped[list[WebhookEvent]] = relationship(back_populates="repository", cascade="all, delete-orphan")


class RepositoryLanguage(Base):
    __tablename__ = "repository_languages"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    percentage: Mapped[float] = mapped_column(default=0.0)

    repository: Mapped[Repository] = relationship(back_populates="languages")
