import structlog

from src.jobs.constants import JobEventTypeEnum, JobStatusEnum
from src.jobs.dto import HandoffJobCreate, JobArtifactCreate, JobEventCreate
from src.jobs.models import HandoffJob
from src.jobs.repositories import HandoffJobRepository, JobArtifactRepository, JobEventRepository
from src.jobs.schemas import HandoffJobCreateRequest


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

    async def get_job(self, job_id: int) -> HandoffJob:
        return await self._handoff_job_repo.get(job_id)
