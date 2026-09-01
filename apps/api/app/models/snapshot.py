from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from .repository import Repository
    from .file import RepositoryFile
    from .job import IndexingJob


class RepositorySnapshot(Base, TimestampMixin):
    __tablename__ = "repository_snapshots"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), default="main")
    parent_shas: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    file_count: Mapped[int] = mapped_column(default=0)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    files_added: Mapped[int] = mapped_column(default=0)
    files_removed: Mapped[int] = mapped_column(default=0)
    files_modified: Mapped[int] = mapped_column(default=0)
    symbols_added: Mapped[int] = mapped_column(default=0)
    symbols_removed: Mapped[int] = mapped_column(default=0)
    indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    repository: Mapped[Repository] = relationship(back_populates="snapshots")
    files: Mapped[list[RepositoryFile]] = relationship(back_populates="last_changed_snapshot", foreign_keys="RepositoryFile.last_changed_snapshot_id")
    jobs: Mapped[list[IndexingJob]] = relationship(back_populates="snapshot")
