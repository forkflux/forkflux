from unittest.mock import AsyncMock, Mock

from src.jobs.constants import JobEventTypeEnum, JobPriorityEnum, JobStatusEnum
from src.jobs.dto import HandoffJobCreate, JobEventCreate
from src.jobs.schemas import HandoffJobCreateRequest, HandoffJobFilterParams, JobArtifact
from src.jobs.services import HandoffJobService


async def test_handoff_job_service_get_job_delegates_and_returns_job() -> None:
    job_id = 123
    expected_job = object()
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    repository.get = AsyncMock(return_value=expected_job)
    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    job = await service.get_job(job_id)

    repository.get.assert_awaited_once_with(job_id)
    assert job == expected_job


async def test_handoff_job_service_list_jobs_delegates_and_returns_jobs() -> None:
    filter_params = HandoffJobFilterParams(limit=50, status=JobStatusEnum.PUBLISHED, target_role_key="reviewer")
    expected_jobs = [Mock(), Mock()]

    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    repository.list = AsyncMock(return_value=expected_jobs)

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    jobs = await service.list_jobs(filter_params=filter_params)

    repository.list.assert_awaited_once_with(filter_params=filter_params)
    assert jobs == expected_jobs


async def test_handoff_job_service_create_job_creates_job_and_bulk_creates_artifacts_and_returns_job_id() -> None:
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()

    created_job = Mock()
    created_job.id = 321

    repository.create = AsyncMock(return_value=created_job)
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    job_data = HandoffJobCreateRequest(
        parent_job_id=None,
        summary="Summarize ticket",
        context_payload={"ticket_id": "TCK-42"},
        target_role_key="reviewer",
        constraints=["deadline:today"],
        artifacts=[
            JobArtifact(
                type="document",
                uri="s3://bucket/doc-1.pdf",
                checksum="checksum-1",
                metadata_json={"mime_type": "application/pdf"},
            ),
            JobArtifact(
                type="trace",
                uri="s3://bucket/trace-1.json",
                checksum=None,
                metadata_json={"mime_type": "application/json"},
            ),
        ],
        priority=JobPriorityEnum.HIGH,
    )

    created_job_id = await service.create_job(job_data=job_data, target_role_id=20, source_agent_id=10)

    expected_job = HandoffJobCreate(
        parent_job_id=job_data.parent_job_id,
        summary=job_data.summary,
        context_payload=job_data.context_payload,
        priority=job_data.priority,
        source_agent_id=10,
        target_role_id=20,
        constraints=job_data.constraints,
    )

    repository.create.assert_awaited_once_with(dto=expected_job)
    job_artifact_repo.bulk_create.assert_awaited_once()
    job_event_repo.create.assert_awaited_once_with(
        dto=JobEventCreate(
            job_id=created_job.id,
            event_type=JobEventTypeEnum.TASK_PUBLISHED.value,
            previous_status=None,
            current_status=JobStatusEnum.PUBLISHED,
            actor_agent_id=10,
            payload_json={
                "priority": job_data.priority.value,
                "target_role_id": 20,
                "artifact_count": 2,
            },
        )
    )

    bulk_create_call = job_artifact_repo.bulk_create.await_args
    bulk_create_dtos = bulk_create_call.kwargs["dtos"]
    artifacts = job_data.artifacts

    assert len(bulk_create_dtos) == 2
    assert all(dto.job_id == created_job.id for dto in bulk_create_dtos)
    assert bulk_create_dtos[0].artifact_type == artifacts[0].type
    assert bulk_create_dtos[0].artifact_uri == artifacts[0].uri
    assert bulk_create_dtos[0].artifact_checksum == artifacts[0].checksum
    assert bulk_create_dtos[0].metadata_json == artifacts[0].metadata_json
    assert bulk_create_dtos[1].artifact_type == artifacts[1].type
    assert bulk_create_dtos[1].artifact_uri == artifacts[1].uri
    assert bulk_create_dtos[1].artifact_checksum == artifacts[1].checksum
    assert bulk_create_dtos[1].metadata_json == artifacts[1].metadata_json
    assert created_job_id == created_job.id
