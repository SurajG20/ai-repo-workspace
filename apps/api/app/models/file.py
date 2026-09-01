from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampUpdateMixin, new_uuid

if TYPE_CHECKING:
    from .repository import Repository
    from .snapshot import RepositorySnapshot


class RepositoryFile(Base, TimestampUpdateMixin):
    __tablename__ = "repository_files"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), default="unknown")
    language: Mapped[str | None] = mapped_column(String(64))
    module_path: Mapped[str | None] = mapped_column(Text)
    package_name: Mapped[str | None] = mapped_column(String(255))
    last_sha: Mapped[str | None] = mapped_column(String(64))
    last_parsed_at: Mapped[datetime | None] = mapped_column()
    last_changed_snapshot_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_snapshots.id")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    repository: Mapped[Repository] = relationship(back_populates="files")
    last_changed_snapshot: Mapped[RepositorySnapshot | None] = relationship(
        back_populates="files", foreign_keys=[last_changed_snapshot_id]
    )
