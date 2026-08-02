from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.repository import JobStatus, JobType

from .base import Base, TimestampUpdateMixin, new_uuid, utcnow


class IndexingJob(Base, TimestampUpdateMixin):
    __tablename__ = "indexing_jobs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    snapshot_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_snapshots.id")
    )
    workflow_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("indexing_workflows.id")
    )
    job_type: Mapped[JobType] = mapped_column(String(32), nullable=False)
    parent_job_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("indexing_jobs.id")
    )
    status: Mapped[JobStatus] = mapped_column(String(32), default=JobStatus.QUEUED)
    priority: Mapped[int] = mapped_column(SmallInteger, default=0)
    progress: Mapped[float] = mapped_column(default=0.0)
    total_files: Mapped[Optional[int]] = mapped_column(Integer)
    processed_files: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    max_retries: Mapped[int] = mapped_column(SmallInteger, default=3)
    locked_by: Mapped[Optional[str]] = mapped_column(String(128))
    locked_at: Mapped[Optional[datetime]] = mapped_column()
    started_at: Mapped[Optional[datetime]] = mapped_column()
    completed_at: Mapped[Optional[datetime]] = mapped_column()
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(128))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    repository: Mapped["Repository"] = relationship(back_populates="jobs")
    snapshot: Mapped[Optional["RepositorySnapshot"]] = relationship(back_populates="jobs")
    workflow: Mapped[Optional["IndexingWorkflow"]] = relationship(back_populates="jobs")
    errors: Mapped[list["IndexingError"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    parent_job: Mapped[Optional["IndexingJob"]] = relationship(remote_side=[id])


class IndexingError(Base):
    __tablename__ = "indexing_errors"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    job_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("indexing_jobs.id"), nullable=False)
    file_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("repository_files.id"))
    error_type: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["IndexingJob"] = relationship(back_populates="errors")


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    worker_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    current_job_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(32), default="idle")
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
