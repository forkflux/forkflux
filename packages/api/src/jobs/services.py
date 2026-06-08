from datetime import datetime, timezone

import structlog
from src.agents.models import AgentIdentity
from src.jobs.constants import JobEventTypeEnum, JobStatusEnum
from src.jobs.dto import (
    HandoffJobCreate,
    HandoffJobItem,
    HandoffJobWithArtifacts,
    JobArtifactCreate,
    JobEventCreate,
)
from src.jobs.exceptions import HandoffJobConflictError
from src.jobs.repositories import HandoffJobRepository, JobArtifactRepository, JobEventRepository
from src.jobs.schemas import HandoffJobCreateRequest, HandoffJobFilterParams


class HandoffJobService:
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
        return await self._handoff_job_repo.get(job_id)

    async def get_job_with_artifacts(self, job_id: int) -> HandoffJobWithArtifacts:
        job = await self._handoff_job_repo.get(job_id)
        artifacts = await self._job_artifact_repo.list(job_id=job_id)
        return {"job": job, "artifacts": artifacts}

    async def list_jobs(self, filter_params: HandoffJobFilterParams) -> list[HandoffJobItem]:
        log = self._logger.bind(
            method="list_jobs",
            status=filter_params.status.value if filter_params.status is not None else None,
            target_role_key=filter_params.target_role_key,
            limit=filter_params.limit,
        )
        log.info("operation_started")

        jobs = await self._handoff_job_repo.list(filter_params=filter_params)

        log.info("operation_completed", jobs_count=len(jobs))
        return jobs

    async def claim_job(self, job_id: int, agent: AgentIdentity) -> None:
        log = self._logger.bind(method="claim_job", job_id=job_id, agent_id=agent.id, agent_role_id=agent.role_id)
        log.info("operation_started")

        job = await self._handoff_job_repo.get_by_id_for_update(job_id=job_id)

        if job.status != JobStatusEnum.PUBLISHED:
            log.warning(
                "operation_failed",
                reason="invalid_status",
                current_status=job.status.value,
            )
            raise HandoffJobConflictError

        if agent.role_id != job.target_role_id:
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

        job.status = JobStatusEnum.CLAIMED
        job.assignee_agent_id = agent.id
        job.claimed_at = datetime.now(timezone.utc)

        await self._handoff_job_repo.save(job=job)
        log.info("operation_completed")
