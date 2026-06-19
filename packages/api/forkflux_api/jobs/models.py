from datetime import datetime
from typing import Any

from forkflux_api.database import Base
from forkflux_api.jobs.constants import JobStatusEnum
from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class HandoffJob(Base):
    __tablename__ = "handoff_job"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(constraints) = 'array'",
            name="chk_constraints_is_array",
        ),
        CheckConstraint(
            "jsonb_typeof(context_payload) = 'object'",
            name="chk_payload_is_object",
        ),
        Index("idx_handoff_job_status_created", "status", text("created_at DESC")),
        Index(
            "idx_handoff_job_assignee_status",
            "assignee_agent_id",
            "status",
            text("created_at DESC"),
        ),
        Index(
            "idx_handoff_job_target_role_status",
            "target_role_id",
            "status",
            text("created_at DESC"),
        ),
        Index(
            "idx_handoff_job_source_status",
            "source_agent_id",
            "status",
            text("created_at DESC"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_job_id: Mapped[int | None] = mapped_column(ForeignKey("handoff_job.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    context_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[JobStatusEnum] = mapped_column(
        Enum(JobStatusEnum, name="job_status", native_enum=True),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    source_agent_id: Mapped[int] = mapped_column(ForeignKey("agent_identity.id"), nullable=False)
    target_role_id: Mapped[int] = mapped_column(ForeignKey("target_role.id"), nullable=False)
    assignee_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agent_identity.id"), nullable=True)

    constraints: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class JobArtifact(Base):
    __tablename__ = "job_artifact"
    __table_args__ = (Index("idx_job_artifact_job", "job_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("handoff_job.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_uri: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class JobEvent(Base):
    __tablename__ = "job_event"
    __table_args__ = (Index("idx_job_event_job_created", "job_id", text("created_at ASC")),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("handoff_job.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    previous_status: Mapped[JobStatusEnum | None] = mapped_column(
        Enum(JobStatusEnum, name="job_status", native_enum=True),
        nullable=True,
    )
    current_status: Mapped[JobStatusEnum] = mapped_column(
        Enum(JobStatusEnum, name="job_status", native_enum=True),
        nullable=False,
    )
    actor_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agent_identity.id"), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
