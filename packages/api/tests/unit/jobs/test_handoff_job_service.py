from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from forkflux_api.jobs.constants import JobEventTypeEnum, JobListOrderEnum, JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.dto import (
    HandoffJobCreate,
    HandoffJobFilterParams,
    HandoffJobItem,
    HandoffJobRawStats,
    JobEventCreate,
)
from forkflux_api.jobs.exceptions import HandoffJobConflictError
from forkflux_api.jobs.schemas import HandoffJobCreateRequest, JobArtifact
from forkflux_api.jobs.services import HandoffJobService


async def test_handoff_job_service_get_job_delegates_and_returns_job() -> None:
    job_id = 123
    expected_job = HandoffJobItem(
        job_details=Mock(),
        target_role_key="reviewer",
        source_agent_label="source-agent",
        assignee_agent_label=None,
    )
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


async def test_handoff_job_service_get_job_with_artifacts_delegates_and_returns_payload() -> None:
    job_id = 123
    expected_job = HandoffJobItem(
        job_details=Mock(),
        target_role_key="reviewer",
        source_agent_label="source-agent",
        assignee_agent_label=None,
    )
    expected_artifacts = [object(), object()]

    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()

    repository.get = AsyncMock(return_value=expected_job)
    job_artifact_repo.list = AsyncMock(return_value=expected_artifacts)

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    result = await service.get_job_with_artifacts(job_id=job_id)

    repository.get.assert_awaited_once_with(job_id)
    job_artifact_repo.list.assert_awaited_once_with(job_id=job_id)
    assert result["job"] is expected_job
    assert result["artifacts"] == expected_artifacts


async def test_handoff_job_service_list_jobs_delegates_and_returns_jobs() -> None:
    filter_params = HandoffJobFilterParams(
        limit=50,
        statuses=[JobStatusEnum.PUBLISHED],
        target_role_ids=[1],
        order=[JobListOrderEnum.CREATED_AT_ASC],
    )
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


async def test_handoff_job_service_delete_job_delegates_to_repository_delete() -> None:
    job_id = 123

    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    repository.delete = AsyncMock()

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    await service.delete_job(job_id=job_id)

    repository.delete.assert_awaited_once_with(job_id=job_id)


async def test_handoff_job_service_stats_computes_completion_rate_and_medians() -> None:
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()

    base = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    repository.stats = AsyncMock(
        return_value=HandoffJobRawStats(
            window_hours=24,
            stuck_minutes=60,
            total_jobs=8,
            all_time_status_counts={
                JobStatusEnum.PUBLISHED: 11,
                JobStatusEnum.CLAIMED: 3,
                JobStatusEnum.IN_PROGRESS: 2,
                JobStatusEnum.COMPLETED: 30,
                JobStatusEnum.FAILED: 4,
                JobStatusEnum.CANCELLED: 1,
            },
            status_counts={
                JobStatusEnum.PUBLISHED: 1,
                JobStatusEnum.CLAIMED: 1,
                JobStatusEnum.IN_PROGRESS: 1,
                JobStatusEnum.COMPLETED: 3,
                JobStatusEnum.FAILED: 1,
                JobStatusEnum.CANCELLED: 1,
            },
            active_agents=8,
            stuck_jobs=2,
            total_handoffs=3,
            waiting_jobs_by_role=[("qa", 8), ("frontend", 2)],
            published_to_claimed_pairs=[
                (base, base + timedelta(minutes=15)),
                (base, base + timedelta(minutes=10)),
                (base + timedelta(minutes=30), base + timedelta(minutes=50)),
                (base + timedelta(minutes=90), base + timedelta(minutes=70)),
            ],
            published_to_resolution_pairs=[
                (base, base + timedelta(minutes=40)),
                (base, base + timedelta(minutes=80)),
                (base, base + timedelta(minutes=30)),
                (base + timedelta(minutes=60), base + timedelta(minutes=55)),
            ],
        )
    )

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    result = await service.stats()

    repository.stats.assert_awaited_once_with(window_hours=24, stuck_minutes=60)
    assert result.window_hours == 24
    assert result.stuck_minutes == 60
    assert result.total_jobs == 8
    assert result.queue_status_counts[JobStatusEnum.PUBLISHED] == 1
    assert result.queue_status_counts[JobStatusEnum.CLAIMED] == 1
    assert result.queue_status_counts[JobStatusEnum.IN_PROGRESS] == 1
    assert result.terminal_status_counts[JobStatusEnum.COMPLETED] == 3
    assert result.terminal_status_counts[JobStatusEnum.FAILED] == 1
    assert result.terminal_status_counts[JobStatusEnum.CANCELLED] == 1
    assert result.all_time_status_counts[JobStatusEnum.COMPLETED] == 30
    assert result.completion_rate == pytest.approx(3 / 8)
    assert result.failure_rate == pytest.approx(1 / 8)
    assert result.active_agents == 8
    assert result.stuck_jobs == 2
    assert result.total_handoffs == 3
    assert result.estimated_time_saved_minutes == 24
    assert result.waiting_jobs_by_role == [("qa", 8), ("frontend", 2)]
    assert result.p50_time_to_claim_minutes == pytest.approx(15.0)
    assert result.p90_time_to_claim_minutes == pytest.approx(19.0)
    assert result.p50_time_to_resolution_minutes == pytest.approx(40.0)
    assert result.p90_time_to_resolution_minutes == pytest.approx(72.0)


async def test_handoff_job_service_stats_returns_zeroed_metrics_for_empty_data() -> None:
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()

    repository.stats = AsyncMock(
        return_value=HandoffJobRawStats(
            window_hours=24,
            stuck_minutes=60,
            total_jobs=0,
            all_time_status_counts={status: 0 for status in JobStatusEnum},
            status_counts={status: 0 for status in JobStatusEnum},
            active_agents=0,
            stuck_jobs=0,
            total_handoffs=0,
            waiting_jobs_by_role=[],
            published_to_claimed_pairs=[],
            published_to_resolution_pairs=[],
        )
    )

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    result = await service.stats()

    repository.stats.assert_awaited_once_with(window_hours=24, stuck_minutes=60)
    assert result.total_jobs == 0
    assert result.completion_rate == 0.0
    assert result.failure_rate == 0.0
    assert result.active_agents == 0
    assert result.stuck_jobs == 0
    assert result.total_handoffs == 0
    assert result.estimated_time_saved_minutes == 0
    assert result.waiting_jobs_by_role == []
    assert result.p50_time_to_claim_minutes is None
    assert result.p90_time_to_claim_minutes is None
    assert result.p50_time_to_resolution_minutes is None
    assert result.p90_time_to_resolution_minutes is None
    for status in JobStatusEnum:
        if status in {JobStatusEnum.PUBLISHED, JobStatusEnum.CLAIMED, JobStatusEnum.IN_PROGRESS}:
            assert result.queue_status_counts[status] == 0
        if status in {JobStatusEnum.COMPLETED, JobStatusEnum.FAILED, JobStatusEnum.CANCELLED}:
            assert result.terminal_status_counts[status] == 0
        assert result.all_time_status_counts[status] == 0


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


async def test_handoff_job_service_claim_job_claims_and_persists_when_checks_pass() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.PUBLISHED
    job.target_role_id = 20
    job.assignee_agent_id = None
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    agent_id = 10
    agent_role_ids = [20]

    await service.claim_job(job_id=123, agent_id=agent_id, agent_role_ids=agent_role_ids)

    repository.get_by_id_for_update.assert_awaited_once_with(job_id=123)
    repository.save.assert_awaited_once_with(job=job)
    assert job.status == JobStatusEnum.IN_PROGRESS
    assert job.assignee_agent_id == 10
    assert isinstance(job.claimed_at, datetime)
    assert isinstance(job.started_at, datetime)


async def test_handoff_job_service_claim_job_raises_conflict_when_status_is_not_published() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.CLAIMED
    job.target_role_id = 20
    job.assignee_agent_id = None
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    with pytest.raises(HandoffJobConflictError):
        await service.claim_job(job_id=123, agent_id=10, agent_role_ids=[20])

    repository.save.assert_not_called()


async def test_handoff_job_service_claim_job_raises_conflict_when_role_mismatch() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.PUBLISHED
    job.target_role_id = 20
    job.assignee_agent_id = None
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    with pytest.raises(HandoffJobConflictError):
        await service.claim_job(job_id=123, agent_id=10, agent_role_ids=[99])

    repository.save.assert_not_called()


async def test_handoff_job_service_claim_job_raises_conflict_when_job_already_assigned() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.PUBLISHED
    job.target_role_id = 20
    job.assignee_agent_id = 77
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    with pytest.raises(HandoffJobConflictError):
        await service.claim_job(job_id=123, agent_id=10, agent_role_ids=[20])

    repository.save.assert_not_called()


async def test_handoff_job_service_change_job_status_sets_started_at_and_saves_for_assignee() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.CLAIMED
    job.assignee_agent_id = 10
    job.source_agent_id = 42
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    await service.change_job_status(job_id=123, status=JobStatusEnum.IN_PROGRESS, agent_id=10)

    repository.get_by_id_for_update.assert_awaited_once_with(job_id=123)
    repository.save.assert_awaited_once_with(job=job)
    assert job.status == JobStatusEnum.IN_PROGRESS
    assert isinstance(job.updated_at, datetime)
    assert isinstance(job.started_at, datetime)


async def test_handoff_job_service_change_job_status_sets_completed_at_for_assignee() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.IN_PROGRESS
    job.assignee_agent_id = 10
    job.source_agent_id = 42
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    await service.change_job_status(job_id=123, status=JobStatusEnum.COMPLETED, agent_id=10)

    repository.save.assert_awaited_once_with(job=job)
    assert job.status == JobStatusEnum.COMPLETED
    assert isinstance(job.updated_at, datetime)
    assert isinstance(job.completed_at, datetime)


async def test_handoff_job_service_change_job_status_sets_failed_at_and_failure_reason_for_assignee() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.IN_PROGRESS
    job.assignee_agent_id = 10
    job.source_agent_id = 42
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    failure_reason = "executor timeout"
    await service.change_job_status(
        job_id=123,
        status=JobStatusEnum.FAILED,
        agent_id=10,
        failure_reason=failure_reason,
    )

    repository.get_by_id_for_update.assert_awaited_once_with(job_id=123)
    repository.save.assert_awaited_once_with(job=job)
    assert job.status == JobStatusEnum.FAILED
    assert isinstance(job.updated_at, datetime)
    assert isinstance(job.failed_at, datetime)
    assert job.failure_reason == failure_reason


async def test_handoff_job_service_change_job_status_allows_source_agent_cancel_for_claimed() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.CLAIMED
    job.assignee_agent_id = 10
    job.source_agent_id = 42
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    await service.change_job_status(job_id=123, status=JobStatusEnum.CANCELLED, agent_id=42)

    repository.save.assert_awaited_once_with(job=job)
    assert job.status == JobStatusEnum.CANCELLED
    assert isinstance(job.updated_at, datetime)
    assert isinstance(job.cancelled_at, datetime)


async def test_handoff_job_service_change_job_status_raises_conflict_for_invalid_transition() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.PUBLISHED
    job.assignee_agent_id = None
    job.source_agent_id = 42
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    with pytest.raises(HandoffJobConflictError):
        await service.change_job_status(job_id=123, status=JobStatusEnum.COMPLETED, agent_id=42)

    repository.save.assert_not_called()


async def test_handoff_job_service_change_job_status_raises_conflict_when_assignee_mismatch() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.CLAIMED
    job.assignee_agent_id = 10
    job.source_agent_id = 42
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    with pytest.raises(HandoffJobConflictError):
        await service.change_job_status(job_id=123, status=JobStatusEnum.IN_PROGRESS, agent_id=99)

    repository.save.assert_not_called()


async def test_handoff_job_service_change_job_status_raises_conflict_when_non_source_cancels_published() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()

    job = Mock()
    job.status = JobStatusEnum.PUBLISHED
    job.assignee_agent_id = None
    job.source_agent_id = 42
    repository.get_by_id_for_update.return_value = job

    service = HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        trace_id="trace-123",
    )

    with pytest.raises(HandoffJobConflictError):
        await service.change_job_status(job_id=123, status=JobStatusEnum.CANCELLED, agent_id=99)

    repository.save.assert_not_called()
