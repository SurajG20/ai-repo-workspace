from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampUpdateMixin, new_uuid


class RepositoryFile(Base, TimestampUpdateMixin):
    __tablename__ = "repository_files"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), default="unknown")
    language: Mapped[Optional[str]] = mapped_column(String(64))
    module_path: Mapped[Optional[str]] = mapped_column(Text)
    package_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_sha: Mapped[Optional[str]] = mapped_column(String(64))
    last_parsed_at: Mapped[Optional[datetime]] = mapped_column()
    last_changed_snapshot_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_snapshots.id")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    repository: Mapped["Repository"] = relationship(back_populates="files")
    last_changed_snapshot: Mapped[Optional["RepositorySnapshot"]] = relationship(
        back_populates="files", foreign_keys=[last_changed_snapshot_id]
    )
