from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, Enum, ForeignKey, Index, Integer, SmallInteger, Text, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from forkflux_api.database import Base, UTCDateTime
from forkflux_api.jobs.constants import JobStatusEnum

JSON_TYPE = JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")
PK_TYPE = BigInteger().with_variant(Integer, "sqlite")


class HandoffJob(Base):
    __tablename__ = "handoff_job"
    __table_args__ = (
        CheckConstraint("jsonb_typeof(constraints) = 'array'", name="chk_constraints_is_array").ddl_if(
            dialect="postgresql"
        ),
        CheckConstraint("jsonb_typeof(context_payload) = 'object'", name="chk_payload_is_object").ddl_if(
            dialect="postgresql"
        ),
        CheckConstraint(
            "json_valid(constraints) AND json_type(constraints) = 'array'", name="chk_constraints_is_array"
        ).ddl_if(dialect="sqlite"),
        CheckConstraint(
            "json_valid(context_payload) AND json_type(context_payload) = 'object'", name="chk_payload_is_object"
        ).ddl_if(dialect="sqlite"),
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

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    parent_job_id: Mapped[int | None] = mapped_column(ForeignKey("handoff_job.id"), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    context_payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    status: Mapped[JobStatusEnum] = mapped_column(
        Enum(JobStatusEnum, name="job_status", native_enum=True),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    source_agent_id: Mapped[int] = mapped_column(ForeignKey("agent_identity.id"), nullable=False)
    target_role_id: Mapped[int] = mapped_column(ForeignKey("target_role.id"), nullable=False)
    assignee_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agent_identity.id"), nullable=True)

    constraints: Mapped[list[Any]] = mapped_column(JSON_TYPE, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    published_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class JobArtifact(Base):
    __tablename__ = "job_artifact"
    __table_args__ = (Index("idx_job_artifact_job", "job_id"),)

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("handoff_job.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_uri: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class JobEvent(Base):
    __tablename__ = "job_event"
    __table_args__ = (Index("idx_job_event_job_created", "job_id", text("created_at ASC")),)

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
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
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
