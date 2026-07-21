from datetime import datetime, timedelta, timezone
from typing import Any, List, cast

import structlog
from sqlalchemy import Row, Select, UnaryExpression, column, func, select, table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from forkflux_api.jobs.constants import JobListOrderEnum, JobStatusEnum
from forkflux_api.jobs.dto import (
    HandoffJobCreate,
    HandoffJobFilterParams,
    HandoffJobItem,
    HandoffJobRawStats,
    HandoffJobUiDetailItem,
    HandoffJobUiItem,
    JobArtifactCreate,
    JobEventCreate,
    JobEventUiItem,
)
from forkflux_api.jobs.exceptions import (
    HandoffJobConflictError,
    HandoffJobHasChildrenError,
    HandoffJobNotFoundError,
    JobArtifactConflictError,
    JobEventConflictError,
)
from forkflux_api.jobs.models import HandoffJob, JobArtifact, JobEvent

MAX_STATS_DURATION_SAMPLES = 200
AGENT_IDENTITY_TABLE = table("agent_identity", column("id"), column("agent_label"))
TARGET_ROLE_TABLE = table("target_role", column("id"), column("role_key"), column("role_label"))
AGENT_API_TOKEN_TABLE = table("agent_api_token", column("agent_id"), column("is_active"), column("last_used_at"))


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
            blocked_reason=None,
            published_at=now,
            claimed_at=None,
            started_at=None,
            completed_at=None,
            failed_at=None,
            blocked_at=None,
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
        source_agent = aliased(AGENT_IDENTITY_TABLE, name="source_agent")
        assignee_agent = aliased(AGENT_IDENTITY_TABLE, name="assignee_agent")

        stmt = (
            select(
                HandoffJob,
                TARGET_ROLE_TABLE.c.role_key,
                source_agent.c.agent_label,
                assignee_agent.c.agent_label,
            )
            .join(TARGET_ROLE_TABLE, HandoffJob.target_role_id == TARGET_ROLE_TABLE.c.id)
            .join(source_agent, HandoffJob.source_agent_id == source_agent.c.id)
            .outerjoin(assignee_agent, HandoffJob.assignee_agent_id == assignee_agent.c.id)
        )
        return cast(Select[tuple[HandoffJob, str, str, str | None]], stmt)

    async def get(self, job_id: int) -> HandoffJobItem:
        stmt = self._base_list_item_stmt().where(HandoffJob.id == job_id)
        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise HandoffJobNotFoundError

        return self._map_row_to_list_item(row)

    @staticmethod
    def _map_row_to_ui_detail_item(row: Row[tuple[Any, ...]]) -> HandoffJobUiDetailItem:
        return HandoffJobUiDetailItem(
            id=row.id,
            parent_job_id=row.parent_job_id,
            parent_job_summary=row.parent_job_summary,
            summary=row.summary,
            context_payload=row.context_payload,
            status=row.status,
            priority=row.priority,
            source_agent_label=row.source_agent_label,
            assignee_agent_label=row.assignee_agent_label,
            target_role_label=row.target_role_label,
            constraints=row.constraints,
            failure_reason=row.failure_reason,
            blocked_reason=row.blocked_reason,
            published_at=row.published_at,
            claimed_at=row.claimed_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
            failed_at=row.failed_at,
            blocked_at=row.blocked_at,
            cancelled_at=row.cancelled_at,
            expires_at=row.expires_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def ui_get(self, job_id: int) -> HandoffJobUiDetailItem:
        log = self._logger.bind(method="ui_get", job_id=job_id)
        log.info("operation_started")

        source_agent = aliased(AGENT_IDENTITY_TABLE, name="ui_detail_source_agent")
        assignee_agent = aliased(AGENT_IDENTITY_TABLE, name="ui_detail_assignee_agent")
        parent_job = aliased(HandoffJob, name="ui_detail_parent_job")

        stmt = (
            select(
                HandoffJob.id.label("id"),
                HandoffJob.parent_job_id.label("parent_job_id"),
                parent_job.summary.label("parent_job_summary"),
                HandoffJob.summary.label("summary"),
                HandoffJob.context_payload.label("context_payload"),
                HandoffJob.status.label("status"),
                HandoffJob.priority.label("priority"),
                source_agent.c.agent_label.label("source_agent_label"),
                assignee_agent.c.agent_label.label("assignee_agent_label"),
                TARGET_ROLE_TABLE.c.role_label.label("target_role_label"),
                HandoffJob.constraints.label("constraints"),
                HandoffJob.failure_reason.label("failure_reason"),
                HandoffJob.blocked_reason.label("blocked_reason"),
                HandoffJob.published_at.label("published_at"),
                HandoffJob.claimed_at.label("claimed_at"),
                HandoffJob.started_at.label("started_at"),
                HandoffJob.completed_at.label("completed_at"),
                HandoffJob.failed_at.label("failed_at"),
                HandoffJob.blocked_at.label("blocked_at"),
                HandoffJob.cancelled_at.label("cancelled_at"),
                HandoffJob.expires_at.label("expires_at"),
                HandoffJob.created_at.label("created_at"),
                HandoffJob.updated_at.label("updated_at"),
            )
            .join(TARGET_ROLE_TABLE, HandoffJob.target_role_id == TARGET_ROLE_TABLE.c.id)
            .join(source_agent, HandoffJob.source_agent_id == source_agent.c.id)
            .outerjoin(assignee_agent, HandoffJob.assignee_agent_id == assignee_agent.c.id)
            .outerjoin(parent_job, HandoffJob.parent_job_id == parent_job.id)
            .where(HandoffJob.id == job_id)
        )

        result = await self._session.execute(stmt)
        row = result.one_or_none()
        if row is None:
            raise HandoffJobNotFoundError

        log.info("operation_completed")
        return self._map_row_to_ui_detail_item(row)

    async def get_by_id_for_update(self, job_id: int) -> HandoffJob:
        stmt = select(HandoffJob).where(HandoffJob.id == job_id).with_for_update()
        result = await self._session.execute(stmt)
        handoff_job = result.scalar_one_or_none()
        if handoff_job is None:
            raise HandoffJobNotFoundError

        return handoff_job

    async def list(self, filter_params: HandoffJobFilterParams) -> List[HandoffJobItem]:
        stmt = self._base_list_item_stmt()

        if filter_params.statuses:
            stmt = stmt.where(HandoffJob.status.in_(filter_params.statuses))

        if filter_params.target_role_ids:
            stmt = stmt.where(HandoffJob.target_role_id.in_(filter_params.target_role_ids))

        order_clauses = self._build_order_clauses(filter_params.order)

        stmt = stmt.order_by(*order_clauses).limit(filter_params.limit)
        result = await self._session.execute(stmt)

        return [self._map_row_to_list_item(row) for row in result.all()]

    @staticmethod
    def _build_order_clauses(order: List[JobListOrderEnum]) -> List[UnaryExpression[Any]]:
        order_clauses = []
        for order_mode in order:
            if order_mode == JobListOrderEnum.CREATED_AT_ASC:
                order_clauses.append(HandoffJob.created_at.asc())
            elif order_mode == JobListOrderEnum.CREATED_AT_DESC:
                order_clauses.append(HandoffJob.created_at.desc())
            elif order_mode == JobListOrderEnum.PRIORITY_ASC:
                order_clauses.append(HandoffJob.priority.asc())
            elif order_mode == JobListOrderEnum.PRIORITY_DESC:
                order_clauses.append(HandoffJob.priority.desc())

        order_clauses.append(HandoffJob.id.asc())
        return order_clauses

    @staticmethod
    def _apply_ui_filters(stmt, filter_params: HandoffJobFilterParams):
        if filter_params.statuses:
            stmt = stmt.where(HandoffJob.status.in_(filter_params.statuses))

        if filter_params.target_role_ids:
            stmt = stmt.where(HandoffJob.target_role_id.in_(filter_params.target_role_ids))

        return stmt

    @staticmethod
    def _map_row_to_ui_item(row: Row[tuple[Any]]) -> HandoffJobUiItem:
        return HandoffJobUiItem(
            id=row.id,
            parent_job_id=row.parent_job_id,
            parent_job_summary=row.parent_job_summary,
            summary=row.summary,
            status=row.status,
            priority=row.priority,
            source_agent_label=row.source_agent_label,
            assignee_agent_label=row.assignee_agent_label,
            target_role_label=row.target_role_label,
            created_at=row.created_at,
        )

    async def ui_list(self, filter_params: HandoffJobFilterParams) -> List[HandoffJobUiItem]:
        log = self._logger.bind(
            method="ui_list",
            statuses=[status.value for status in filter_params.statuses],
            target_role_ids=filter_params.target_role_ids,
            limit=filter_params.limit,
            offset=filter_params.offset,
            order=[order.value for order in filter_params.order],
        )
        log.info("operation_started")

        source_agent = aliased(AGENT_IDENTITY_TABLE, name="ui_source_agent")
        assignee_agent = aliased(AGENT_IDENTITY_TABLE, name="ui_assignee_agent")
        parent_job = aliased(HandoffJob, name="ui_parent_job")

        stmt = (
            select(
                HandoffJob.id.label("id"),
                HandoffJob.parent_job_id.label("parent_job_id"),
                parent_job.summary.label("parent_job_summary"),
                HandoffJob.summary.label("summary"),
                HandoffJob.status.label("status"),
                HandoffJob.priority.label("priority"),
                source_agent.c.agent_label.label("source_agent_label"),
                assignee_agent.c.agent_label.label("assignee_agent_label"),
                TARGET_ROLE_TABLE.c.role_label.label("target_role_label"),
                HandoffJob.created_at.label("created_at"),
            )
            .join(TARGET_ROLE_TABLE, HandoffJob.target_role_id == TARGET_ROLE_TABLE.c.id)
            .join(source_agent, HandoffJob.source_agent_id == source_agent.c.id)
            .outerjoin(assignee_agent, HandoffJob.assignee_agent_id == assignee_agent.c.id)
            .outerjoin(parent_job, HandoffJob.parent_job_id == parent_job.id)
        )

        stmt = self._apply_ui_filters(stmt, filter_params)
        order_clauses = self._build_order_clauses(filter_params.order)
        stmt = stmt.order_by(*order_clauses).limit(filter_params.limit).offset(filter_params.offset)

        result = await self._session.execute(stmt)
        items = [self._map_row_to_ui_item(row) for row in result.all()]

        log.info("operation_completed", items_count=len(items))
        return items

    async def ui_count(self, filter_params: HandoffJobFilterParams) -> int:
        log = self._logger.bind(
            method="ui_count",
            statuses=[status.value for status in filter_params.statuses],
            target_role_ids=filter_params.target_role_ids,
        )
        log.info("operation_started")

        stmt = select(func.count(HandoffJob.id))
        stmt = self._apply_ui_filters(stmt, filter_params)

        total = int((await self._session.scalar(stmt)) or 0)

        log.info("operation_completed", total=total)
        return total

    async def count_by_status(self) -> dict[JobStatusEnum, int]:
        status_counts: dict[JobStatusEnum, int] = {status: 0 for status in JobStatusEnum}
        status_rows = await self._session.execute(
            select(HandoffJob.status, func.count(HandoffJob.id)).group_by(HandoffJob.status)
        )
        for status, count in status_rows.all():
            status_counts[status] = int(count)

        return status_counts

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

    async def stats(self, window_hours: int = 24, stuck_minutes: int = 60) -> HandoffJobRawStats:
        log = self._logger.bind(method="stats")

        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=window_hours)
        stuck_before = now - timedelta(minutes=stuck_minutes)

        active_statuses = [JobStatusEnum.PUBLISHED, JobStatusEnum.CLAIMED, JobStatusEnum.IN_PROGRESS]

        total_jobs = int(
            (
                await self._session.scalar(
                    select(func.count(HandoffJob.id)).where(HandoffJob.published_at >= window_start)
                )
            )
            or 0
        )

        all_time_status_counts: dict[JobStatusEnum, int] = {status: 0 for status in JobStatusEnum}
        all_time_status_rows = await self._session.execute(
            select(HandoffJob.status, func.count(HandoffJob.id)).group_by(HandoffJob.status)
        )
        for status, count in all_time_status_rows.all():
            all_time_status_counts[status] = int(count)

        status_counts: dict[JobStatusEnum, int] = {status: 0 for status in JobStatusEnum}
        status_rows = await self._session.execute(
            select(HandoffJob.status, func.count(HandoffJob.id))
            .where(HandoffJob.published_at >= window_start)
            .group_by(HandoffJob.status)
        )
        for status, count in status_rows.all():
            status_counts[status] = int(count)

        active_agents = int(
            (
                await self._session.scalar(
                    select(func.count(func.distinct(AGENT_API_TOKEN_TABLE.c.agent_id))).where(
                        AGENT_API_TOKEN_TABLE.c.is_active.is_(True),
                        AGENT_API_TOKEN_TABLE.c.last_used_at.is_not(None),
                        AGENT_API_TOKEN_TABLE.c.last_used_at >= window_start,
                    )
                )
            )
            or 0
        )

        stuck_jobs = int(
            (
                await self._session.scalar(
                    select(func.count(HandoffJob.id)).where(
                        HandoffJob.status.in_(active_statuses),
                        HandoffJob.updated_at < stuck_before,
                    )
                )
            )
            or 0
        )

        total_handoffs = int(
            (
                await self._session.scalar(
                    select(func.count(HandoffJob.id)).where(
                        HandoffJob.published_at >= window_start,
                        HandoffJob.status == JobStatusEnum.COMPLETED,
                        HandoffJob.claimed_at.is_not(None),
                    )
                )
            )
            or 0
        )

        waiting_jobs_by_role_rows = await self._session.execute(
            select(TARGET_ROLE_TABLE.c.role_key, func.count(HandoffJob.id))
            .join(TARGET_ROLE_TABLE, HandoffJob.target_role_id == TARGET_ROLE_TABLE.c.id)
            .where(
                HandoffJob.status == JobStatusEnum.PUBLISHED,
                HandoffJob.published_at >= window_start,
            )
            .group_by(TARGET_ROLE_TABLE.c.role_key)
            .order_by(func.count(HandoffJob.id).desc(), TARGET_ROLE_TABLE.c.role_key.asc())
            .limit(3)
        )
        waiting_jobs_by_role = [(role_key, int(count)) for role_key, count in waiting_jobs_by_role_rows.all()]

        published_to_claimed_rows = await self._session.execute(
            select(HandoffJob.published_at, HandoffJob.claimed_at)
            .where(
                HandoffJob.published_at >= window_start,
                HandoffJob.claimed_at.is_not(None),
            )
            .order_by(HandoffJob.published_at.desc(), HandoffJob.id.desc())
            .limit(MAX_STATS_DURATION_SAMPLES)
        )
        published_to_claimed_pairs = [
            (published_at, claimed_at) for published_at, claimed_at in published_to_claimed_rows.all()
        ]

        published_to_resolution_rows = await self._session.execute(
            select(
                HandoffJob.published_at,
                func.coalesce(HandoffJob.completed_at, HandoffJob.failed_at, HandoffJob.cancelled_at),
            )
            .where(
                HandoffJob.published_at >= window_start,
                HandoffJob.status.in_([JobStatusEnum.COMPLETED, JobStatusEnum.FAILED, JobStatusEnum.CANCELLED]),
                func.coalesce(HandoffJob.completed_at, HandoffJob.failed_at, HandoffJob.cancelled_at).is_not(None),
            )
            .order_by(HandoffJob.published_at.desc(), HandoffJob.id.desc())
            .limit(MAX_STATS_DURATION_SAMPLES)
        )
        published_to_resolution_pairs = [
            (published_at, resolved_at) for published_at, resolved_at in published_to_resolution_rows.all()
        ]

        log.info(
            "operation_completed",
            window_hours=window_hours,
            stuck_minutes=stuck_minutes,
            total_jobs=total_jobs,
            completed_jobs=status_counts[JobStatusEnum.COMPLETED],
            failed_jobs=status_counts[JobStatusEnum.FAILED],
            active_agents=active_agents,
            stuck_jobs=stuck_jobs,
            total_handoffs=total_handoffs,
            published_to_claimed_samples=len(published_to_claimed_pairs),
            published_to_resolution_samples=len(published_to_resolution_pairs),
            duration_sample_cap=MAX_STATS_DURATION_SAMPLES,
        )

        return HandoffJobRawStats(
            window_hours=window_hours,
            stuck_minutes=stuck_minutes,
            total_jobs=total_jobs,
            all_time_status_counts=all_time_status_counts,
            status_counts=status_counts,
            active_agents=active_agents,
            stuck_jobs=stuck_jobs,
            total_handoffs=total_handoffs,
            waiting_jobs_by_role=waiting_jobs_by_role,
            published_to_claimed_pairs=published_to_claimed_pairs,
            published_to_resolution_pairs=published_to_resolution_pairs,
        )


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
            event_type=dto.event_type.value,
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

    @staticmethod
    def _map_row_to_ui_item(row: Row[tuple[Any]]) -> JobEventUiItem:
        return JobEventUiItem(
            event_type=row.event_type,
            previous_status=row.previous_status,
            current_status=row.current_status,
            actor_agent_label=row.actor_agent_label,
            payload_json=row.payload_json,
            created_at=row.created_at,
        )

    async def ui_list(self, job_id: int) -> list[JobEventUiItem]:
        log = self._logger.bind(method="ui_list", job_id=job_id)
        log.info("operation_started")

        actor_agent = aliased(AGENT_IDENTITY_TABLE, name="ui_actor_agent")

        stmt = (
            select(
                JobEvent.event_type.label("event_type"),
                JobEvent.previous_status.label("previous_status"),
                JobEvent.current_status.label("current_status"),
                actor_agent.c.agent_label.label("actor_agent_label"),
                JobEvent.payload_json.label("payload_json"),
                JobEvent.created_at.label("created_at"),
            )
            .outerjoin(actor_agent, JobEvent.actor_agent_id == actor_agent.c.id)
            .where(JobEvent.job_id == job_id)
            .order_by(JobEvent.created_at.desc(), JobEvent.id.desc())
        )

        result = await self._session.execute(stmt)
        items = [self._map_row_to_ui_item(row) for row in result.all()]

        log.info("operation_completed", events_count=len(items))
        return items
