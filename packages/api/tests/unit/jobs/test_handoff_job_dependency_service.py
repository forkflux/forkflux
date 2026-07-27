from unittest.mock import ANY, AsyncMock, Mock

import pytest
from forkflux_api.jobs.constants import (
    DependencyTypeEnum,
    JobEventTypeEnum,
    JobPriorityEnum,
    JobStatusEnum,
)
from forkflux_api.jobs.exceptions import HandoffJobConflictError, HandoffJobNotFoundError
from forkflux_api.jobs.mcp_schemas import HandoffJobCreateRequest
from forkflux_api.jobs.services import HandoffJobService


def _build_create_request(**overrides) -> HandoffJobCreateRequest:
    defaults = {
        "parent_job_id": None,
        "summary": "Dependency test job",
        "context_payload": {"task": "implement feature"},
        "target_role_key": "backend",
        "constraints": ["deadline:today"],
        "artifacts": [],
        "priority": JobPriorityEnum.NORMAL,
    }
    defaults.update(overrides)
    return HandoffJobCreateRequest(**defaults)


def _make_service(
    repository: Mock | None = None,
    job_artifact_repo: Mock | None = None,
    job_event_repo: Mock | None = None,
    job_dependency_repo: Mock | None = None,
) -> HandoffJobService:
    repo = repository or Mock()
    artifact_repo = job_artifact_repo or Mock()
    artifact_repo.bulk_create = AsyncMock()
    event_repo = job_event_repo or Mock()
    event_repo.create = AsyncMock()
    dep_repo = job_dependency_repo or Mock()
    return HandoffJobService(
        handoff_job_repo=repo,
        job_artifact_repo=artifact_repo,
        job_event_repo=event_repo,
        job_dependency_repo=dep_repo,
        trace_id="trace-dep-test",
    )


async def test_create_job_with_blocked_by_creates_pending_job_and_dependency_edges() -> None:
    repository = Mock()
    repository.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.bulk_create = AsyncMock()
    job_dependency_repo.count_unmet_blockers = AsyncMock(return_value=1)
    job_dependency_repo.find_failed_blockers = AsyncMock(return_value=[])
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()

    created_job = Mock()
    created_job.id = 100
    created_job.status = JobStatusEnum.PENDING
    repository.create.return_value = created_job

    service = _make_service(
        repository=repository,
        job_dependency_repo=job_dependency_repo,
        job_event_repo=job_event_repo,
    )

    job_data = _build_create_request(blocked_by=[1, 2])

    await service.create_job(job_data, target_role_id=10, source_agent_id=20)

    repository.create.assert_awaited_once_with(
        dto=ANY,
        status=JobStatusEnum.PENDING,
    )

    job_dependency_repo.bulk_create.assert_awaited_once()
    call_args = job_dependency_repo.bulk_create.await_args
    dtos = call_args.kwargs["dtos"]
    assert len(dtos) == 2
    assert all(dto.dep_type == DependencyTypeEnum.BLOCKS for dto in dtos)
    assert {dto.upstream_job_id for dto in dtos} == {1, 2}
    assert all(dto.downstream_job_id == 100 for dto in dtos)

    job_event_repo.create.assert_awaited_once()
    event_dto = job_event_repo.create.await_args.kwargs["dto"]
    assert event_dto.event_type == JobEventTypeEnum.TASK_PENDING
    assert event_dto.current_status == JobStatusEnum.PENDING


async def test_create_job_with_blocked_by_all_completed_transitions_to_published() -> None:
    repository = Mock()
    repository.create = AsyncMock()
    repository.save = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.bulk_create = AsyncMock()
    job_dependency_repo.count_unmet_blockers = AsyncMock(return_value=0)
    job_dependency_repo.find_failed_blockers = AsyncMock(return_value=[])
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()

    created_job = Mock()
    created_job.id = 100
    created_job.status = JobStatusEnum.PENDING
    repository.create.return_value = created_job

    service = _make_service(
        repository=repository,
        job_dependency_repo=job_dependency_repo,
        job_event_repo=job_event_repo,
    )

    job_data = _build_create_request(blocked_by=[1, 2])

    await service.create_job(job_data, target_role_id=10, source_agent_id=20)

    repository.save.assert_awaited_once()
    assert created_job.status == JobStatusEnum.PUBLISHED

    event_dto = job_event_repo.create.await_args.kwargs["dto"]
    assert event_dto.event_type == JobEventTypeEnum.TASK_ACTIVATED
    assert event_dto.current_status == JobStatusEnum.PUBLISHED


async def test_create_job_without_blocked_by_creates_published_job() -> None:
    repository = Mock()
    repository.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.bulk_create = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()

    created_job = Mock()
    created_job.id = 100
    repository.create.return_value = created_job

    service = _make_service(
        repository=repository,
        job_dependency_repo=job_dependency_repo,
        job_event_repo=job_event_repo,
    )

    job_data = _build_create_request()

    await service.create_job(job_data, target_role_id=10, source_agent_id=20)

    repository.create.assert_awaited_once_with(dto=ANY, status=JobStatusEnum.PUBLISHED)
    job_dependency_repo.bulk_create.assert_not_awaited()

    event_dto = job_event_repo.create.await_args.kwargs["dto"]
    assert event_dto.event_type == JobEventTypeEnum.TASK_PUBLISHED


async def test_change_job_status_completed_triggers_barrier_sync() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.find_downstream_pending_job_ids = AsyncMock(return_value=[200])
    job_dependency_repo.count_unmet_blockers = AsyncMock(return_value=0)

    completed_job = Mock()
    completed_job.status = JobStatusEnum.IN_PROGRESS
    completed_job.assignee_agent_id = 10
    completed_job.source_agent_id = 42
    completed_job.routing_rules = None
    repository.get_by_id_for_update.return_value = completed_job

    downstream_job = Mock()
    downstream_job.status = JobStatusEnum.PENDING
    downstream_job.id = 200

    # First call returns completed_job, second returns downstream_job
    repository.get_by_id_for_update.side_effect = [completed_job, downstream_job]

    service = _make_service(
        repository=repository,
        job_event_repo=job_event_repo,
        job_dependency_repo=job_dependency_repo,
    )

    await service.change_job_status(job_id=1, status=JobStatusEnum.COMPLETED, agent_id=10)

    job_dependency_repo.find_downstream_pending_job_ids.assert_awaited_once_with(upstream_job_id=1)
    job_dependency_repo.count_unmet_blockers.assert_awaited_once_with(downstream_job_id=200)

    assert downstream_job.status == JobStatusEnum.PUBLISHED
    repository.save.assert_awaited()

    # Should have created 2 events: one for COMPLETED, one for TASK_ACTIVATED
    # (routing_rules is None so no TASK_ROUTED event is created)
    assert job_event_repo.create.await_count == 2
    second_event = job_event_repo.create.await_args_list[1].kwargs["dto"]
    assert second_event.event_type == JobEventTypeEnum.TASK_ACTIVATED
    assert second_event.current_status == JobStatusEnum.PUBLISHED


async def test_change_job_status_completed_does_not_activate_downstream_with_unmet_blockers() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.find_downstream_pending_job_ids = AsyncMock(return_value=[200])
    job_dependency_repo.count_unmet_blockers = AsyncMock(return_value=1)

    completed_job = Mock()
    completed_job.status = JobStatusEnum.IN_PROGRESS
    completed_job.assignee_agent_id = 10
    completed_job.source_agent_id = 42
    completed_job.routing_rules = None
    repository.get_by_id_for_update.return_value = completed_job

    service = _make_service(
        repository=repository,
        job_event_repo=job_event_repo,
        job_dependency_repo=job_dependency_repo,
    )

    await service.change_job_status(job_id=1, status=JobStatusEnum.COMPLETED, agent_id=10)

    # Only the COMPLETED event, no TASK_ACTIVATED
    assert job_event_repo.create.await_count == 1


async def test_change_job_status_pending_to_cancelled_allowed_for_source_agent() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.find_downstream_pending_job_ids = AsyncMock(return_value=[])

    pending_job = Mock()
    pending_job.status = JobStatusEnum.PENDING
    pending_job.source_agent_id = 42
    pending_job.assignee_agent_id = None
    repository.get_by_id_for_update.return_value = pending_job

    service = _make_service(
        repository=repository,
        job_event_repo=job_event_repo,
        job_dependency_repo=job_dependency_repo,
    )

    await service.change_job_status(job_id=1, status=JobStatusEnum.CANCELLED, agent_id=42)

    assert pending_job.status == JobStatusEnum.CANCELLED


async def test_change_job_status_pending_to_cancelled_rejected_for_non_source_agent() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()
    job_dependency_repo = Mock()

    pending_job = Mock()
    pending_job.status = JobStatusEnum.PENDING
    pending_job.source_agent_id = 42
    pending_job.assignee_agent_id = None
    repository.get_by_id_for_update.return_value = pending_job

    service = _make_service(
        repository=repository,
        job_event_repo=job_event_repo,
        job_dependency_repo=job_dependency_repo,
    )

    import pytest

    with pytest.raises(HandoffJobConflictError):
        await service.change_job_status(job_id=1, status=JobStatusEnum.CANCELLED, agent_id=99)


async def test_reject_job_creates_reopen_iteration_with_incremented_retry_count() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.create = AsyncMock()
    repository.save = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.bulk_create = AsyncMock()
    job_dependency_repo.has_blocks_edge = AsyncMock(return_value=True)
    job_dependency_repo.delete_blocks_edge = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()

    # The reviewing job (job_id=60) — must be IN_PROGRESS and assigned to the caller.
    reviewing_job = Mock()
    reviewing_job.id = 60
    reviewing_job.status = JobStatusEnum.IN_PROGRESS
    reviewing_job.assignee_agent_id = 70

    # The original job (target_job_id=50) — must be COMPLETED.
    original_job = Mock()
    original_job.id = 50
    original_job.status = JobStatusEnum.COMPLETED
    original_job.retry_count = 1
    original_job.max_retries = 3
    original_job.parent_job_id = None
    original_job.summary = "Original work"
    original_job.context_payload = {"task": "implement"}
    original_job.priority = JobPriorityEnum.HIGH.value
    original_job.target_role_id = 10
    original_job.constraints = ["deadline:today"]

    # First call returns reviewing_job, second returns original_job.
    repository.get_by_id_for_update.side_effect = [reviewing_job, original_job]

    new_job = Mock()
    new_job.id = 51
    repository.create.return_value = new_job

    service = _make_service(
        repository=repository,
        job_dependency_repo=job_dependency_repo,
        job_event_repo=job_event_repo,
    )

    result = await service.reject_job(
        job_id=60,
        target_job_id=50,
        reason="Tests failed",
        source_agent_id=70,
    )

    assert result == (51, 2)

    repository.create.assert_awaited_once()
    create_call = repository.create.await_args
    assert create_call.kwargs["status"] == JobStatusEnum.PUBLISHED
    create_dto = create_call.kwargs["dto"]
    assert create_dto.retry_count == 2
    assert create_dto.max_retries == 3
    assert create_dto.parent_job_id is None

    job_dependency_repo.bulk_create.assert_awaited_once()
    dep_dtos = job_dependency_repo.bulk_create.await_args.kwargs["dtos"]
    assert len(dep_dtos) == 2
    assert dep_dtos[0].dep_type == DependencyTypeEnum.REOPEN_OF
    assert dep_dtos[0].upstream_job_id == 50
    assert dep_dtos[0].downstream_job_id == 51
    assert dep_dtos[1].dep_type == DependencyTypeEnum.BLOCKS
    assert dep_dtos[1].upstream_job_id == 51
    assert dep_dtos[1].downstream_job_id == 60

    # Old BLOCKS edge deleted.
    job_dependency_repo.delete_blocks_edge.assert_awaited_once_with(upstream_job_id=50, downstream_job_id=60)

    # Reviewer transitioned to PENDING.
    assert reviewing_job.status == JobStatusEnum.PENDING
    repository.save.assert_awaited()

    # Two events: retry published + reviewer pending.
    assert job_event_repo.create.await_count == 2
    retry_event = job_event_repo.create.await_args_list[0].kwargs["dto"]
    assert retry_event.event_type == JobEventTypeEnum.TASK_PUBLISHED
    assert retry_event.payload_json["retry_count"] == 2
    assert retry_event.payload_json["rejection_reason"] == "Tests failed"
    reviewer_event = job_event_repo.create.await_args_list[1].kwargs["dto"]
    assert reviewer_event.event_type == JobEventTypeEnum.TASK_PENDING
    assert reviewer_event.current_status == JobStatusEnum.PENDING


async def test_reject_job_raises_conflict_when_caller_not_assignee() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()

    reviewing_job = Mock()
    reviewing_job.status = JobStatusEnum.IN_PROGRESS
    reviewing_job.assignee_agent_id = 70
    repository.get_by_id_for_update.return_value = reviewing_job

    service = _make_service(repository=repository)

    import pytest

    with pytest.raises(HandoffJobConflictError):
        await service.reject_job(
            job_id=60,
            target_job_id=50,
            reason="unauthorized",
            source_agent_id=99,
        )


async def test_reject_job_raises_conflict_when_reviewing_job_not_in_progress() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()

    reviewing_job = Mock()
    reviewing_job.status = JobStatusEnum.PUBLISHED
    reviewing_job.assignee_agent_id = 70
    repository.get_by_id_for_update.return_value = reviewing_job

    service = _make_service(repository=repository)

    import pytest

    with pytest.raises(HandoffJobConflictError):
        await service.reject_job(
            job_id=60,
            target_job_id=50,
            reason="wrong status",
            source_agent_id=70,
        )


async def test_reject_job_raises_conflict_when_target_not_completed() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()

    reviewing_job = Mock()
    reviewing_job.status = JobStatusEnum.IN_PROGRESS
    reviewing_job.assignee_agent_id = 70

    original_job = Mock()
    original_job.status = JobStatusEnum.IN_PROGRESS

    repository.get_by_id_for_update.side_effect = [reviewing_job, original_job]

    service = _make_service(repository=repository)

    import pytest

    with pytest.raises(HandoffJobConflictError):
        await service.reject_job(
            job_id=60,
            target_job_id=50,
            reason="target not done",
            source_agent_id=70,
        )


async def test_reject_job_truncates_oversized_reason() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.create = AsyncMock()
    repository.save = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.bulk_create = AsyncMock()
    job_dependency_repo.has_blocks_edge = AsyncMock(return_value=True)
    job_dependency_repo.delete_blocks_edge = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()

    reviewing_job = Mock()
    reviewing_job.status = JobStatusEnum.IN_PROGRESS
    reviewing_job.assignee_agent_id = 70

    original_job = Mock()
    original_job.id = 50
    original_job.status = JobStatusEnum.COMPLETED
    original_job.retry_count = 0
    original_job.max_retries = 3
    original_job.parent_job_id = None
    original_job.summary = "Original work"
    original_job.context_payload = {"task": "implement"}
    original_job.priority = JobPriorityEnum.NORMAL.value
    original_job.target_role_id = 10
    original_job.constraints = []

    repository.get_by_id_for_update.side_effect = [reviewing_job, original_job]

    new_job = Mock()
    new_job.id = 51
    repository.create.return_value = new_job

    service = _make_service(
        repository=repository,
        job_dependency_repo=job_dependency_repo,
        job_event_repo=job_event_repo,
    )

    long_reason = "x" * 3000
    await service.reject_job(
        job_id=60,
        target_job_id=50,
        reason=long_reason,
        source_agent_id=70,
    )

    # The first event is the retry job's TASK_PUBLISHED event with the rejection reason.
    retry_event = job_event_repo.create.await_args_list[0].kwargs["dto"]
    assert len(retry_event.payload_json["rejection_reason"]) == 2000


async def test_reject_job_raises_not_found_when_reviewing_job_missing() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock(side_effect=HandoffJobNotFoundError)

    service = _make_service(repository=repository)
    with pytest.raises(HandoffJobNotFoundError) as exc_info:
        await service.reject_job(
            job_id=999,
            target_job_id=50,
            reason="not found",
            source_agent_id=70,
        )

    # The service must tag the error so the handler can attribute it to the
    # reviewing job (path job_id), not to target_job_id.
    assert exc_info.value.which == "job_id"


async def test_reject_job_raises_conflict_when_max_retries_exceeded() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.has_blocks_edge = AsyncMock(return_value=True)
    job_dependency_repo.delete_blocks_edge = AsyncMock()

    reviewing_job = Mock()
    reviewing_job.status = JobStatusEnum.IN_PROGRESS
    reviewing_job.assignee_agent_id = 70

    # Original job has exhausted its retry budget.
    original_job = Mock()
    original_job.status = JobStatusEnum.COMPLETED
    original_job.retry_count = 3
    original_job.max_retries = 3

    repository.get_by_id_for_update.side_effect = [reviewing_job, original_job]

    service = _make_service(repository=repository, job_dependency_repo=job_dependency_repo)

    import pytest

    with pytest.raises(HandoffJobConflictError):
        await service.reject_job(
            job_id=60,
            target_job_id=50,
            reason="max retries exceeded",
            source_agent_id=70,
        )


async def test_reject_job_raises_conflict_when_no_blocks_edge() -> None:
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.has_blocks_edge = AsyncMock(return_value=False)

    reviewing_job = Mock()
    reviewing_job.status = JobStatusEnum.IN_PROGRESS
    reviewing_job.assignee_agent_id = 70

    original_job = Mock()
    original_job.status = JobStatusEnum.COMPLETED
    original_job.retry_count = 0
    original_job.max_retries = 3

    repository.get_by_id_for_update.side_effect = [reviewing_job, original_job]

    service = _make_service(repository=repository, job_dependency_repo=job_dependency_repo)

    import pytest

    with pytest.raises(HandoffJobConflictError):
        await service.reject_job(
            job_id=60,
            target_job_id=50,
            reason="no edge",
            source_agent_id=70,
        )


# ---------------------------------------------------------------------------
# Terminal-failure propagation tests
# ---------------------------------------------------------------------------


async def test_create_job_with_already_failed_upstream_transitions_to_failed() -> None:
    """When an upstream blocker is already FAILED at creation time, the new job
    should be immediately transitioned to FAILED with provenance instead of
    remaining stuck in PENDING."""
    repository = Mock()
    repository.create = AsyncMock()
    repository.save = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.bulk_create = AsyncMock()
    job_dependency_repo.find_failed_blockers = AsyncMock(return_value=[(1, JobStatusEnum.FAILED)])
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()

    created_job = Mock()
    created_job.id = 100
    created_job.status = JobStatusEnum.PENDING
    repository.create.return_value = created_job

    service = _make_service(
        repository=repository,
        job_dependency_repo=job_dependency_repo,
        job_event_repo=job_event_repo,
    )

    job_data = _build_create_request(blocked_by=[1, 2])

    await service.create_job(job_data, target_role_id=10, source_agent_id=20)

    # Job should be transitioned to FAILED
    assert created_job.status == JobStatusEnum.FAILED
    repository.save.assert_awaited_once()

    # Event should be TASK_FAILED
    event_dto = job_event_repo.create.await_args.kwargs["dto"]
    assert event_dto.event_type == JobEventTypeEnum.TASK_FAILED
    assert event_dto.current_status == JobStatusEnum.FAILED

    # count_unmet_blockers should NOT have been called (failed check short-circuits)
    job_dependency_repo.count_unmet_blockers.assert_not_called()


async def test_create_job_with_already_cancelled_upstream_transitions_to_cancelled() -> None:
    """When an upstream blocker is already CANCELLED at creation time, the new
    job should be immediately transitioned to CANCELLED with provenance."""
    repository = Mock()
    repository.create = AsyncMock()
    repository.save = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.bulk_create = AsyncMock()
    job_dependency_repo.find_failed_blockers = AsyncMock(return_value=[(1, JobStatusEnum.CANCELLED)])
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()

    created_job = Mock()
    created_job.id = 100
    created_job.status = JobStatusEnum.PENDING
    repository.create.return_value = created_job

    service = _make_service(
        repository=repository,
        job_dependency_repo=job_dependency_repo,
        job_event_repo=job_event_repo,
    )

    job_data = _build_create_request(blocked_by=[1, 2])

    await service.create_job(job_data, target_role_id=10, source_agent_id=20)

    assert created_job.status == JobStatusEnum.CANCELLED
    repository.save.assert_awaited_once()

    event_dto = job_event_repo.create.await_args.kwargs["dto"]
    assert event_dto.event_type == JobEventTypeEnum.TASK_CANCELLED
    assert event_dto.current_status == JobStatusEnum.CANCELLED


async def test_change_job_status_failed_propagates_to_downstream_pending() -> None:
    """When a job transitions to FAILED, downstream PENDING jobs with this job
    as a blocker should be propagated to FAILED with provenance."""
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.find_downstream_pending_job_ids = AsyncMock(return_value=[200])
    job_dependency_repo.find_failed_blockers = AsyncMock(return_value=[(1, JobStatusEnum.FAILED)])

    failed_job = Mock()
    failed_job.status = JobStatusEnum.IN_PROGRESS
    failed_job.assignee_agent_id = 10
    failed_job.source_agent_id = 42
    failed_job.routing_rules = None

    downstream_job = Mock()
    downstream_job.status = JobStatusEnum.PENDING
    downstream_job.id = 200

    repository.get_by_id_for_update.side_effect = [failed_job, downstream_job]

    service = _make_service(
        repository=repository,
        job_event_repo=job_event_repo,
        job_dependency_repo=job_dependency_repo,
    )

    await service.change_job_status(job_id=1, status=JobStatusEnum.FAILED, agent_id=10)

    # Downstream should be transitioned to FAILED
    assert downstream_job.status == JobStatusEnum.FAILED

    # Should have created 2 events: one for the upstream FAILED, one for downstream TASK_FAILED
    assert job_event_repo.create.await_count == 2
    downstream_event = job_event_repo.create.await_args_list[1].kwargs["dto"]
    assert downstream_event.event_type == JobEventTypeEnum.TASK_FAILED
    assert downstream_event.current_status == JobStatusEnum.FAILED
    assert downstream_event.payload_json["failed_by"] == 1
    assert downstream_event.payload_json["upstream_terminal_status"] == "failed"
    assert downstream_event.payload_json["reason"] == "barrier_sync_upstream_terminal_failure"


async def test_change_job_status_cancelled_propagates_to_downstream_pending() -> None:
    """When a job transitions to CANCELLED, downstream PENDING jobs with this
    job as a blocker should be propagated to CANCELLED with provenance."""
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.find_downstream_pending_job_ids = AsyncMock(return_value=[200])
    job_dependency_repo.find_failed_blockers = AsyncMock(return_value=[(1, JobStatusEnum.CANCELLED)])

    cancelled_job = Mock()
    cancelled_job.status = JobStatusEnum.PUBLISHED
    cancelled_job.assignee_agent_id = None
    cancelled_job.source_agent_id = 42
    cancelled_job.routing_rules = None

    downstream_job = Mock()
    downstream_job.status = JobStatusEnum.PENDING
    downstream_job.id = 200

    repository.get_by_id_for_update.side_effect = [cancelled_job, downstream_job]

    service = _make_service(
        repository=repository,
        job_event_repo=job_event_repo,
        job_dependency_repo=job_dependency_repo,
    )

    await service.change_job_status(job_id=1, status=JobStatusEnum.CANCELLED, agent_id=42)

    # Downstream should be transitioned to CANCELLED
    assert downstream_job.status == JobStatusEnum.CANCELLED

    assert job_event_repo.create.await_count == 2
    downstream_event = job_event_repo.create.await_args_list[1].kwargs["dto"]
    assert downstream_event.event_type == JobEventTypeEnum.TASK_CANCELLED
    assert downstream_event.current_status == JobStatusEnum.CANCELLED
    assert downstream_event.payload_json["upstream_terminal_status"] == "cancelled"


async def test_change_job_status_failed_does_not_propagate_without_failed_blockers() -> None:
    """When a job transitions to FAILED but downstream jobs have no terminally-
    failed blockers (e.g. other blockers still in progress), the downstream
    job should remain PENDING."""
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.find_downstream_pending_job_ids = AsyncMock(return_value=[200])
    job_dependency_repo.find_failed_blockers = AsyncMock(return_value=[])

    failed_job = Mock()
    failed_job.status = JobStatusEnum.IN_PROGRESS
    failed_job.assignee_agent_id = 10
    failed_job.source_agent_id = 42
    failed_job.routing_rules = None
    repository.get_by_id_for_update.return_value = failed_job

    service = _make_service(
        repository=repository,
        job_event_repo=job_event_repo,
        job_dependency_repo=job_dependency_repo,
    )

    await service.change_job_status(job_id=1, status=JobStatusEnum.FAILED, agent_id=10)

    # Only the upstream FAILED event, no downstream propagation
    assert job_event_repo.create.await_count == 1
    # get_by_id_for_update should only have been called once (for the upstream job)
    assert repository.get_by_id_for_update.await_count == 1
