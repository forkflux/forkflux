from datetime import datetime, timezone
from math import ceil, floor
from statistics import median

import structlog

from forkflux_api.jobs.constants import JobEventTypeEnum, JobStatusEnum
from forkflux_api.jobs.dto import (
    HandoffJobCreate,
    HandoffJobFilterParams,
    HandoffJobItem,
    HandoffJobRawStats,
    HandoffJobStats,
    HandoffJobWithArtifacts,
    JobArtifactCreate,
    JobEventCreate,
)
from forkflux_api.jobs.exceptions import HandoffJobConflictError
from forkflux_api.jobs.repositories import HandoffJobRepository, JobArtifactRepository, JobEventRepository
from forkflux_api.jobs.schemas import HandoffJobCreateRequest


class HandoffJobService:
    MINUTES_SAVED_PER_HANDOFF = 8  # this number is taken from team measurement

    def __init__(
        self,
        handoff_job_repo: HandoffJobRepository,
        job_artifact_repo: JobArtifactRepository,
        job_event_repo: JobEventRepository,
        trace_id: str,
    ) -> None:
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)
        self._handoff_job_repo = handoff_job_repo
        self._job_artifact_repo = job_artifact_repo
        self._job_event_repo = job_event_repo

    @staticmethod
    def _duration_minutes(started_at: datetime, finished_at: datetime) -> float:
        return (finished_at - started_at).total_seconds() / 60

    @staticmethod
    def _median_or_none(values: list[float]) -> float | None:
        if not values:
            return None

        return float(median(values))

    @staticmethod
    def _percentile_or_none(values: list[float], percentile: float) -> float | None:
        if not values:
            return None

        sorted_values = sorted(values)
        position = (len(sorted_values) - 1) * percentile
        lower_idx = floor(position)
        upper_idx = ceil(position)

        if lower_idx == upper_idx:
            return float(sorted_values[lower_idx])

        lower = sorted_values[lower_idx]
        upper = sorted_values[upper_idx]
        weight = position - lower_idx
        return float(lower + ((upper - lower) * weight))

    async def stats(self, window_hours: int = 24, stuck_minutes: int = 60) -> HandoffJobStats:
        log = self._logger.bind(method="stats", window_hours=window_hours, stuck_minutes=stuck_minutes)
        log.info("operation_started")

        raw_stats: HandoffJobRawStats = await self._handoff_job_repo.stats(
            window_hours=window_hours,
            stuck_minutes=stuck_minutes,
        )
        status_counts = {status: raw_stats.status_counts.get(status, 0) for status in JobStatusEnum}
        all_time_status_counts = {status: raw_stats.all_time_status_counts.get(status, 0) for status in JobStatusEnum}
        queue_status_counts = {
            JobStatusEnum.PUBLISHED: status_counts[JobStatusEnum.PUBLISHED],
            JobStatusEnum.CLAIMED: status_counts[JobStatusEnum.CLAIMED],
            JobStatusEnum.IN_PROGRESS: status_counts[JobStatusEnum.IN_PROGRESS],
        }
        terminal_status_counts = {
            JobStatusEnum.COMPLETED: status_counts[JobStatusEnum.COMPLETED],
            JobStatusEnum.FAILED: status_counts[JobStatusEnum.FAILED],
            JobStatusEnum.CANCELLED: status_counts[JobStatusEnum.CANCELLED],
        }

        completed_jobs = status_counts[JobStatusEnum.COMPLETED]
        failed_jobs = status_counts[JobStatusEnum.FAILED]
        total_handoffs = raw_stats.total_handoffs
        estimated_time_saved_minutes = total_handoffs * self.MINUTES_SAVED_PER_HANDOFF
        completion_rate = (completed_jobs / raw_stats.total_jobs) if raw_stats.total_jobs > 0 else 0.0
        failure_rate = (failed_jobs / raw_stats.total_jobs) if raw_stats.total_jobs > 0 else 0.0

        time_to_claim_minutes = [
            self._duration_minutes(published_at, claimed_at)
            for published_at, claimed_at in raw_stats.published_to_claimed_pairs
            if published_at is not None and claimed_at is not None and claimed_at >= published_at
        ]
        time_to_resolution_minutes = [
            self._duration_minutes(published_at, resolved_at)
            for published_at, resolved_at in raw_stats.published_to_resolution_pairs
            if published_at is not None and resolved_at is not None and resolved_at >= published_at
        ]

        log.info(
            "operation_completed",
            total_jobs=raw_stats.total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            active_agents=raw_stats.active_agents,
            stuck_jobs=raw_stats.stuck_jobs,
            total_handoffs=total_handoffs,
            estimated_time_saved_minutes=estimated_time_saved_minutes,
            time_to_claim_samples=len(time_to_claim_minutes),
            time_to_resolution_samples=len(time_to_resolution_minutes),
        )

        return HandoffJobStats(
            window_hours=raw_stats.window_hours,
            stuck_minutes=raw_stats.stuck_minutes,
            total_jobs=raw_stats.total_jobs,
            all_time_status_counts=all_time_status_counts,
            queue_status_counts=queue_status_counts,
            terminal_status_counts=terminal_status_counts,
            completion_rate=completion_rate,
            failure_rate=failure_rate,
            active_agents=raw_stats.active_agents,
            stuck_jobs=raw_stats.stuck_jobs,
            total_handoffs=total_handoffs,
            estimated_time_saved_minutes=estimated_time_saved_minutes,
            waiting_jobs_by_role=raw_stats.waiting_jobs_by_role,
            p50_time_to_claim_minutes=self._median_or_none(time_to_claim_minutes),
            p90_time_to_claim_minutes=self._percentile_or_none(time_to_claim_minutes, 0.9),
            p50_time_to_resolution_minutes=self._median_or_none(time_to_resolution_minutes),
            p90_time_to_resolution_minutes=self._percentile_or_none(time_to_resolution_minutes, 0.9),
        )

    async def create_job(self, job_data: HandoffJobCreateRequest, target_role_id: int, source_agent_id: int) -> int:
        log = self._logger.bind(method="create_job")
        log.info("operation_started")

        job = HandoffJobCreate(
            parent_job_id=job_data.parent_job_id,
            summary=job_data.summary,
            context_payload=job_data.context_payload,
            priority=job_data.priority,
            source_agent_id=source_agent_id,
            target_role_id=target_role_id,
            constraints=job_data.constraints,
        )

        created_job = await self._handoff_job_repo.create(dto=job)
        log = log.bind(job_id=created_job.id)

        artifact_dtos = [
            JobArtifactCreate(
                job_id=created_job.id,
                artifact_type=artifact.type,
                artifact_uri=artifact.uri,
                artifact_checksum=artifact.checksum,
                metadata_json=artifact.metadata_json,
            )
            for artifact in job_data.artifacts
        ]
        await self._job_artifact_repo.bulk_create(dtos=artifact_dtos)

        await self._job_event_repo.create(
            dto=JobEventCreate(
                job_id=created_job.id,
                event_type=JobEventTypeEnum.TASK_PUBLISHED.value,
                previous_status=None,
                current_status=JobStatusEnum.PUBLISHED,
                actor_agent_id=source_agent_id,
                payload_json={
                    "priority": job_data.priority.value,
                    "target_role_id": target_role_id,
                    "artifact_count": len(artifact_dtos),
                },
            )
        )

        log.info("operation_completed", artifact_count=len(artifact_dtos))
        return created_job.id

    async def get_job(self, job_id: int) -> HandoffJobItem:
        log = self._logger.bind(method="get_job", job_id=job_id)
        log.info("operation_started")

        job = await self._handoff_job_repo.get(job_id)

        log.info("operation_completed")
        return job

    async def get_job_with_artifacts(self, job_id: int) -> HandoffJobWithArtifacts:
        log = self._logger.bind(method="get_job_with_artifacts", job_id=job_id)
        log.info("operation_started")

        job = await self._handoff_job_repo.get(job_id)
        artifacts = await self._job_artifact_repo.list(job_id=job_id)

        log.info("operation_completed", artifact_count=len(artifacts))
        return {"job": job, "artifacts": artifacts}

    async def list_jobs(self, filter_params: HandoffJobFilterParams) -> list[HandoffJobItem]:
        log = self._logger.bind(
            method="list_jobs",
            statuses=[status.value for status in filter_params.statuses],
            target_role_ids=filter_params.target_role_ids,
            limit=filter_params.limit,
            order=[order.value for order in filter_params.order],
        )
        log.info("operation_started")

        jobs = await self._handoff_job_repo.list(filter_params=filter_params)

        log.info("operation_completed", jobs_count=len(jobs))
        return jobs

    async def delete_job(self, job_id: int) -> None:
        log = self._logger.bind(method="delete_job", job_id=job_id)
        log.info("operation_started")

        await self._handoff_job_repo.delete(job_id=job_id)

        log.info("operation_completed")

    async def claim_job(self, job_id: int, agent_id: int, agent_role_ids: list[int]) -> None:
        log = self._logger.bind(method="claim_job", job_id=job_id, agent_id=agent_id, agent_role_ids=agent_role_ids)
        log.info("operation_started")

        job = await self._handoff_job_repo.get_by_id_for_update(job_id=job_id)

        if job.status != JobStatusEnum.PUBLISHED:
            log.warning(
                "operation_failed",
                reason="invalid_status",
                current_status=job.status.value,
            )
            raise HandoffJobConflictError

        if job.target_role_id not in agent_role_ids:
            log.warning(
                "operation_failed",
                reason="role_mismatch",
                target_role_id=job.target_role_id,
            )
            raise HandoffJobConflictError

        if job.assignee_agent_id is not None:
            log.warning(
                "operation_failed",
                reason="already_assigned",
                assignee_agent_id=job.assignee_agent_id,
            )
            raise HandoffJobConflictError

        timestamp = datetime.now(timezone.utc)

        job.status = JobStatusEnum.IN_PROGRESS
        job.assignee_agent_id = agent_id
        job.claimed_at = timestamp
        job.started_at = timestamp

        await self._handoff_job_repo.save(job=job)
        log.info("operation_completed")

    async def change_job_status(
        self, job_id: int, status: JobStatusEnum, agent_id: int, failure_reason: str | None = None
    ) -> None:
        log = self._logger.bind(
            method="change_job_status", job_id=job_id, target_status=status.value, agent_id=agent_id
        )
        log.info("operation_started")

        job = await self._handoff_job_repo.get_by_id_for_update(job_id=job_id)
        current_status = job.status

        allowed_transitions = {
            (JobStatusEnum.CLAIMED, JobStatusEnum.IN_PROGRESS),
            (JobStatusEnum.IN_PROGRESS, JobStatusEnum.COMPLETED),
            (JobStatusEnum.IN_PROGRESS, JobStatusEnum.FAILED),
            (JobStatusEnum.CLAIMED, JobStatusEnum.FAILED),
            (JobStatusEnum.PUBLISHED, JobStatusEnum.CANCELLED),
            (JobStatusEnum.CLAIMED, JobStatusEnum.CANCELLED),
        }

        if (current_status, status) not in allowed_transitions:
            log.warning(
                "operation_failed",
                reason="invalid_status_transition",
                current_status=current_status.value,
            )
            raise HandoffJobConflictError

        if current_status == JobStatusEnum.PUBLISHED and status == JobStatusEnum.CANCELLED:
            if job.source_agent_id != agent_id:
                log.warning(
                    "operation_failed",
                    reason="source_agent_mismatch",
                    source_agent_id=job.source_agent_id,
                )
                raise HandoffJobConflictError
        elif current_status == JobStatusEnum.CLAIMED and status == JobStatusEnum.CANCELLED:
            allowed_agent_ids = {job.source_agent_id, job.assignee_agent_id}
            if agent_id not in allowed_agent_ids:
                log.warning(
                    "operation_failed",
                    reason="agent_not_allowed_to_cancel_claimed_job",
                    source_agent_id=job.source_agent_id,
                    assignee_agent_id=job.assignee_agent_id,
                )
                raise HandoffJobConflictError
        elif job.assignee_agent_id != agent_id:
            log.warning(
                "operation_failed",
                reason="assignee_mismatch",
                assignee_agent_id=job.assignee_agent_id,
            )
            raise HandoffJobConflictError

        timestamp = datetime.now(timezone.utc)
        job.status = status
        job.updated_at = timestamp

        if status == JobStatusEnum.IN_PROGRESS:
            job.started_at = timestamp
        elif status == JobStatusEnum.COMPLETED:
            job.completed_at = timestamp
        elif status == JobStatusEnum.FAILED:
            job.failure_reason = failure_reason
            job.failed_at = timestamp
        elif status == JobStatusEnum.CANCELLED:
            job.cancelled_at = timestamp

        await self._handoff_job_repo.save(job=job)
        log.info("operation_completed", previous_status=current_status.value, current_status=status.value)
