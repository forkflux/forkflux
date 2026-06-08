from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from src.agents.models import AgentIdentity, TargetRole
from src.jobs.constants import JobStatusEnum
from src.jobs.dto import HandoffJobCreate, HandoffJobListItem, JobArtifactCreate, JobEventCreate
from src.jobs.exceptions import (
    HandoffJobConflictError,
    HandoffJobNotFoundError,
    JobArtifactConflictError,
    JobEventConflictError,
)
from src.jobs.models import HandoffJob, JobArtifact, JobEvent
from src.jobs.schemas import HandoffJobFilterParams


class HandoffJobRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def create(self, dto: HandoffJobCreate) -> HandoffJob:
        now = datetime.now(timezone.utc)

        handoff_job = HandoffJob(
            parent_job_id=dto.parent_job_id,
            summary=dto.summary,
            context_payload=dto.context_payload,
            status=JobStatusEnum.PUBLISHED,
            priority=dto.priority,
            source_agent_id=dto.source_agent_id,
            target_role_id=dto.target_role_id,
            assignee_agent_id=None,
            constraints=dto.constraints,
            failure_reason=None,
            published_at=now,
            claimed_at=None,
            started_at=None,
            completed_at=None,
            failed_at=None,
            cancelled_at=None,
            expires_at=None,
            created_at=now,
            updated_at=now,
        )

        self._session.add(handoff_job)
        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise HandoffJobConflictError from err

        return handoff_job

    async def get(self, job_id: int) -> HandoffJob:
        result = await self._session.execute(select(HandoffJob).where(HandoffJob.id == job_id))
        handoff_job = result.scalar_one_or_none()
        if handoff_job is None:
            raise HandoffJobNotFoundError

        return handoff_job

    async def list(self, filter_params: HandoffJobFilterParams) -> list[HandoffJobListItem]:
        source_agent = aliased(AgentIdentity)
        assignee_agent = aliased(AgentIdentity)

        stmt = (
            select(
                HandoffJob,
                TargetRole.role_key,
                source_agent.agent_label,
                assignee_agent.agent_label,
            )
            .join(TargetRole, HandoffJob.target_role_id == TargetRole.id)
            .join(source_agent, HandoffJob.source_agent_id == source_agent.id)
            .outerjoin(assignee_agent, HandoffJob.assignee_agent_id == assignee_agent.id)
        )

        if filter_params.status is not None:
            stmt = stmt.where(HandoffJob.status == filter_params.status)

        if filter_params.target_role_key is not None:
            stmt = stmt.where(TargetRole.role_key == filter_params.target_role_key)

        stmt = stmt.order_by(HandoffJob.created_at.asc()).limit(filter_params.limit)
        result = await self._session.execute(stmt)

        return [
            HandoffJobListItem(
                job=job,
                target_role_key=target_role_key,
                source_agent_label=source_agent_label,
                assignee_agent_label=assignee_agent_label,
            )
            for job, target_role_key, source_agent_label, assignee_agent_label in result.all()
        ]


class JobArtifactRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def create(self, dto: JobArtifactCreate) -> JobArtifact:
        job_artifact = JobArtifact(
            job_id=dto.job_id,
            artifact_type=dto.artifact_type,
            artifact_uri=dto.artifact_uri,
            artifact_checksum=dto.artifact_checksum,
            metadata_json=dto.metadata_json,
            created_at=datetime.now(timezone.utc),
        )

        self._session.add(job_artifact)
        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise JobArtifactConflictError from err

        return job_artifact

    async def bulk_create(self, dtos: list[JobArtifactCreate]) -> list[JobArtifact]:
        if not dtos:
            return []

        now = datetime.now(timezone.utc)
        job_artifacts = [
            JobArtifact(
                job_id=dto.job_id,
                artifact_type=dto.artifact_type,
                artifact_uri=dto.artifact_uri,
                artifact_checksum=dto.artifact_checksum,
                metadata_json=dto.metadata_json,
                created_at=now,
            )
            for dto in dtos
        ]

        self._session.add_all(job_artifacts)
        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise JobArtifactConflictError from err

        return job_artifacts


class JobEventRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def create(self, dto: JobEventCreate) -> JobEvent:
        job_event = JobEvent(
            job_id=dto.job_id,
            event_type=dto.event_type,
            previous_status=dto.previous_status,
            current_status=dto.current_status,
            actor_agent_id=dto.actor_agent_id,
            payload_json=dto.payload_json,
            created_at=datetime.now(timezone.utc),
        )

        self._session.add(job_event)
        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise JobEventConflictError from err

        return job_event
