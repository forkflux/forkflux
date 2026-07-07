from datetime import datetime, timezone
from typing import cast

import structlog
from forkflux_api.agents.models import AgentIdentity, TargetRole
from forkflux_api.jobs.constants import JobListOrderEnum, JobStatusEnum
from forkflux_api.jobs.dto import (
    HandoffJobCreate,
    HandoffJobFilterParams,
    HandoffJobItem,
    JobArtifactCreate,
    JobEventCreate,
)
from forkflux_api.jobs.exceptions import (
    HandoffJobConflictError,
    HandoffJobHasChildrenError,
    HandoffJobNotFoundError,
    JobArtifactConflictError,
    JobEventConflictError,
)
from forkflux_api.jobs.models import HandoffJob, JobArtifact, JobEvent
from sqlalchemy import Row, Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased


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

    async def save(self, job: HandoffJob) -> HandoffJob:
        job.updated_at = datetime.now(timezone.utc)

        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise HandoffJobConflictError from err

        return job

    @staticmethod
    def _map_row_to_list_item(
        row: Row[tuple[HandoffJob, str, str, str | None]],
    ) -> HandoffJobItem:
        job, target_role_key, source_agent_label, assignee_agent_label = row
        return HandoffJobItem(
            job_details=job,
            target_role_key=target_role_key,
            source_agent_label=source_agent_label,
            assignee_agent_label=assignee_agent_label,
        )

    @staticmethod
    def _base_list_item_stmt() -> Select[tuple[HandoffJob, str, str, str | None]]:
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
        return cast(Select[tuple[HandoffJob, str, str, str | None]], stmt)

    async def get(self, job_id: int) -> HandoffJobItem:
        stmt = self._base_list_item_stmt().where(HandoffJob.id == job_id)
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise HandoffJobNotFoundError

        return self._map_row_to_list_item(row)

    async def get_by_id_for_update(self, job_id: int) -> HandoffJob:
        stmt = select(HandoffJob).where(HandoffJob.id == job_id).with_for_update()
        result = await self._session.execute(stmt)
        handoff_job = result.scalar_one_or_none()
        if handoff_job is None:
            raise HandoffJobNotFoundError

        return handoff_job

    async def list(self, filter_params: HandoffJobFilterParams) -> list[HandoffJobItem]:
        stmt = self._base_list_item_stmt()

        if filter_params.status is not None:
            stmt = stmt.where(HandoffJob.status == filter_params.status)

        if filter_params.target_role_id is not None:
            stmt = stmt.where(HandoffJob.target_role_id == filter_params.target_role_id)

        order_clauses = []
        for order_mode in filter_params.order:
            if order_mode == JobListOrderEnum.CREATED_AT_ASC:
                order_clauses.append(HandoffJob.created_at.asc())
            elif order_mode == JobListOrderEnum.CREATED_AT_DESC:
                order_clauses.append(HandoffJob.created_at.desc())
            elif order_mode == JobListOrderEnum.PRIORITY_ASC:
                order_clauses.append(HandoffJob.priority.asc())
            elif order_mode == JobListOrderEnum.PRIORITY_DESC:
                order_clauses.append(HandoffJob.priority.desc())

        order_clauses.append(HandoffJob.id.asc())

        stmt = stmt.order_by(*order_clauses).limit(filter_params.limit)
        result = await self._session.execute(stmt)

        return [self._map_row_to_list_item(row) for row in result.all()]

    async def delete(self, job_id: int) -> None:
        log = self._logger.bind(method="delete", job_id=job_id)

        handoff_job = await self._session.get(HandoffJob, job_id)
        if handoff_job is None:
            raise HandoffJobNotFoundError

        child_exists = await self._session.scalar(
            select(HandoffJob.id).where(HandoffJob.parent_job_id == job_id).limit(1)
        )
        if child_exists is not None:
            log.warning("delete_blocked_has_child_jobs")
            raise HandoffJobHasChildrenError

        await self._session.delete(handoff_job)
        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise HandoffJobConflictError from err


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

    async def list(self, job_id: int) -> list[JobArtifact]:
        result = await self._session.execute(
            select(JobArtifact).where(JobArtifact.job_id == job_id).order_by(JobArtifact.created_at.asc())
        )

        return list(result.scalars().all())


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
