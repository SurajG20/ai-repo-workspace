from __future__ import annotations

from typing import Optional

from sqlalchemy import ForeignKey, SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.repository import JobType

from .base import Base, TimestampMixin, new_uuid, utcnow


class IndexingWorkflow(Base, TimestampMixin):
    __tablename__ = "indexing_workflows"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    repository_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    workflow_type: Mapped[JobType] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    total_steps: Mapped[int] = mapped_column(SmallInteger, default=0)
    completed_steps: Mapped[int] = mapped_column(SmallInteger, default=0)
    error_message: Mapped[Optional[str]] = mapped_column()
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    repository: Mapped["Repository"] = relationship(back_populates="workflows")
    jobs: Mapped[list["IndexingJob"]] = relationship(back_populates="workflow")
