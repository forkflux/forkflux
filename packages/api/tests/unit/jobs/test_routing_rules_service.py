from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from forkflux_api.jobs.constants import JobEventTypeEnum, JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.dto import RoutingRuleCreate
from forkflux_api.jobs.exceptions import HandoffJobConflictError
from forkflux_api.jobs.mcp_schemas import HandoffJobCreateRequest, RoutingRule
from forkflux_api.jobs.models import HandoffJob
from forkflux_api.jobs.services import HandoffJobService


def _make_service(
    repository: Mock | None = None,
    job_artifact_repo: Mock | None = None,
    job_event_repo: Mock | None = None,
    job_dependency_repo: Mock | None = None,
) -> HandoffJobService:
    return HandoffJobService(
        handoff_job_repo=repository or Mock(),
        job_artifact_repo=job_artifact_repo or Mock(),
        job_event_repo=job_event_repo or Mock(),
        job_dependency_repo=job_dependency_repo or Mock(),
        trace_id="trace-routing-123",
    )


def _make_completed_job(
    job_id: int = 100,
    source_agent_id: int = 10,
    routing_rules: list[RoutingRule] | None = None,
) -> Mock:
    job = Mock(spec=HandoffJob)
    job.id = job_id
    job.source_agent_id = source_agent_id
    job.status = JobStatusEnum.IN_PROGRESS
    job.assignee_agent_id = source_agent_id
    job.routing_rules = routing_rules
    job.retry_count = 0
    job.max_retries = 3
    job.parent_job_id = None
    job.priority = JobPriorityEnum.NORMAL.value
    job.constraints = []
    job.context_payload = {}
    job.failure_reason = None
    job.blocked_reason = None
    job.unblock_reason = None
    job.cancelled_at = None
    job.failed_at = None
    job.blocked_at = None
    job.unblocked_at = None
    job.unblock_reason = None
    job.published_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    job.claimed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    job.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    job.completed_at = None
    job.expires_at = None
    job.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    job.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return job


# ---------------------------------------------------------------------------
# create_job with routing_rules
# ---------------------------------------------------------------------------


async def test_create_job_passes_routing_rules_to_repository() -> None:
    """create_job must pass routing_rules through to the HandoffJobCreate DTO."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    created_job = Mock()
    created_job.id = 321
    repository.create = AsyncMock(return_value=created_job)
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    routing_rules = [
        RoutingRuleCreate(
            target_role_id=5,
            target_role_key="reviewer",
            summary="Review the work",
            context_payload={"review_type": "code_review"},
            constraints=["must approve before merge"],
            priority=JobPriorityEnum.NORMAL,
            artifacts=[],
        )
    ]

    job_data = HandoffJobCreateRequest(
        parent_job_id=None,
        summary="Build the feature",
        context_payload={"feature": "auth"},
        target_role_key="backend",
        constraints=["deadline:today"],
        artifacts=[],
        priority=JobPriorityEnum.HIGH,
    )

    await service.create_job(
        job_data=job_data,
        target_role_id=20,
        source_agent_id=10,
        routing_rules=routing_rules,
    )

    repository.create.assert_awaited_once()
    create_call = repository.create.await_args
    dto = create_call.kwargs["dto"]
    assert dto.routing_rules is routing_rules


async def test_create_job_with_none_routing_rules_passes_none() -> None:
    """create_job with routing_rules=None must pass None through."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    created_job = Mock()
    created_job.id = 321
    repository.create = AsyncMock(return_value=created_job)
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    job_data = HandoffJobCreateRequest(
        parent_job_id=None,
        summary="Build the feature",
        context_payload={"feature": "auth"},
        target_role_key="backend",
        constraints=["deadline:today"],
        artifacts=[],
        priority=JobPriorityEnum.HIGH,
    )

    await service.create_job(
        job_data=job_data,
        target_role_id=20,
        source_agent_id=10,
        routing_rules=None,
    )

    dto = repository.create.await_args.kwargs["dto"]
    assert dto.routing_rules is None


# ---------------------------------------------------------------------------
# _evaluate_routing_rules — no-op cases
# ---------------------------------------------------------------------------


async def test_evaluate_routing_rules_noop_when_rules_none() -> None:
    """When routing_rules is None, _evaluate_routing_rules returns empty list and creates nothing."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    completed_job = _make_completed_job(routing_rules=None)

    result = await service._evaluate_routing_rules(completed_job=completed_job, actor_agent_id=10)

    assert result == []
    repository.create_in_savepoint.assert_not_called()
    job_event_repo.create.assert_not_called()


async def test_evaluate_routing_rules_noop_when_rules_empty() -> None:
    """When routing_rules is an empty list, _evaluate_routing_rules returns empty list."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    completed_job = _make_completed_job(routing_rules=[])

    result = await service._evaluate_routing_rules(completed_job=completed_job, actor_agent_id=10)

    assert result == []
    repository.create_in_savepoint.assert_not_called()
    job_event_repo.create.assert_not_called()


# ---------------------------------------------------------------------------
# _evaluate_routing_rules — creates downstream jobs
# ---------------------------------------------------------------------------


async def test_evaluate_routing_rules_creates_downstream_job_on_completion() -> None:
    """When routing_rules has one rule, _evaluate_routing_rules creates one PUBLISHED job."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    created_job = Mock()
    created_job.id = 200
    repository.create_in_savepoint = AsyncMock(return_value=created_job)
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    routing_rules = [
        {
            "target_role_id": 5,
            "target_role_key": "reviewer",
            "summary": "Review the completed work",
            "context_payload": {"review_type": "code_review"},
            "constraints": ["must approve before merge"],
            "priority": JobPriorityEnum.NORMAL.value,
            "artifacts": [],
        }
    ]
    completed_job = _make_completed_job(job_id=100, source_agent_id=10, routing_rules=routing_rules)

    result = await service._evaluate_routing_rules(completed_job=completed_job, actor_agent_id=10)

    assert result == [200]
    repository.create_in_savepoint.assert_awaited_once()
    create_dto = repository.create_in_savepoint.await_args.kwargs["dto"]
    assert create_dto.parent_job_id == 100
    assert create_dto.source_agent_id == 10
    assert create_dto.target_role_id == 5
    assert create_dto.summary == "Review the completed work"
    assert create_dto.context_payload["routed_from_job_id"] == 100
    assert create_dto.context_payload["review_type"] == "code_review"
    assert create_dto.constraints == ["must approve before merge"]
    assert repository.create_in_savepoint.await_args.kwargs["status"] == JobStatusEnum.PUBLISHED


async def test_evaluate_routing_rules_creates_multiple_downstream_jobs() -> None:
    """When routing_rules has multiple rules, _evaluate_routing_rules creates multiple jobs."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    job1 = Mock()
    job1.id = 201
    job2 = Mock()
    job2.id = 202
    repository.create_in_savepoint = AsyncMock(side_effect=[job1, job2])
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    routing_rules = [
        {
            "target_role_id": 5,
            "target_role_key": "reviewer",
            "summary": "Review the work",
            "context_payload": {},
            "constraints": [],
            "priority": JobPriorityEnum.NORMAL.value,
            "artifacts": [],
        },
        {
            "target_role_id": 6,
            "target_role_key": "deployer",
            "summary": "Deploy the work",
            "context_payload": {},
            "constraints": [],
            "priority": JobPriorityEnum.HIGH.value,
            "artifacts": [],
        },
    ]
    completed_job = _make_completed_job(job_id=100, source_agent_id=10, routing_rules=routing_rules)

    result = await service._evaluate_routing_rules(completed_job=completed_job, actor_agent_id=10)

    assert result == [201, 202]
    assert repository.create_in_savepoint.await_count == 2


async def test_evaluate_routing_rules_creates_artifacts_for_routed_job() -> None:
    """When a routing rule has artifacts, they are bulk_created for the new job."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    created_job = Mock()
    created_job.id = 200
    repository.create_in_savepoint = AsyncMock(return_value=created_job)
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    routing_rules = [
        {
            "target_role_id": 5,
            "target_role_key": "reviewer",
            "summary": "Review the work",
            "context_payload": {},
            "constraints": [],
            "priority": JobPriorityEnum.NORMAL.value,
            "artifacts": [
                {
                    "type": "document",
                    "uri": "s3://bucket/review-doc.pdf",
                    "checksum": "abc123",
                    "metadata_json": {"mime_type": "application/pdf"},
                }
            ],
        }
    ]
    completed_job = _make_completed_job(job_id=100, source_agent_id=10, routing_rules=routing_rules)

    await service._evaluate_routing_rules(completed_job=completed_job, actor_agent_id=10)

    job_artifact_repo.bulk_create.assert_awaited_once()
    artifact_dtos = job_artifact_repo.bulk_create.await_args.kwargs["dtos"]
    assert len(artifact_dtos) == 1
    assert artifact_dtos[0].job_id == 200
    assert artifact_dtos[0].artifact_type == "document"
    assert artifact_dtos[0].artifact_uri == "s3://bucket/review-doc.pdf"
    assert artifact_dtos[0].artifact_checksum == "abc123"


async def test_evaluate_routing_rules_creates_task_published_event_with_routing_provenance() -> None:
    """Each routed job gets a TASK_PUBLISHED event with routed_from_job_id."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    created_job = Mock()
    created_job.id = 200
    repository.create_in_savepoint = AsyncMock(return_value=created_job)
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    routing_rules = [
        {
            "target_role_id": 5,
            "target_role_key": "reviewer",
            "summary": "Review the work",
            "context_payload": {},
            "constraints": [],
            "priority": JobPriorityEnum.NORMAL.value,
            "artifacts": [],
        }
    ]
    completed_job = _make_completed_job(job_id=100, source_agent_id=10, routing_rules=routing_rules)

    await service._evaluate_routing_rules(completed_job=completed_job, actor_agent_id=10)

    # Two events: one TASK_PUBLISHED for the routed job, one TASK_ROUTED for the completing job
    assert job_event_repo.create.await_count == 2

    published_event = job_event_repo.create.await_args_list[0].kwargs["dto"]
    assert published_event.job_id == 200
    assert published_event.event_type == JobEventTypeEnum.TASK_PUBLISHED
    assert published_event.current_status == JobStatusEnum.PUBLISHED
    assert published_event.payload_json["routed_from_job_id"] == 100

    routed_event = job_event_repo.create.await_args_list[1].kwargs["dto"]
    assert routed_event.job_id == 100
    assert routed_event.event_type == JobEventTypeEnum.TASK_ROUTED
    assert routed_event.current_status == JobStatusEnum.COMPLETED
    assert routed_event.payload_json["routed_job_ids"] == [200]


# ---------------------------------------------------------------------------
# _evaluate_routing_rules — graceful degradation
# ---------------------------------------------------------------------------


async def test_evaluate_routing_rules_skips_rule_with_fk_violation() -> None:
    """When a routing rule's target_role_id causes an FK violation, skip it gracefully."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    # First rule fails with FK violation, second succeeds
    good_job = Mock()
    good_job.id = 202
    repository.create_in_savepoint = AsyncMock(side_effect=[HandoffJobConflictError, good_job])
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    routing_rules = [
        {
            "target_role_id": 999,  # deleted role
            "target_role_key": "stale-role",
            "summary": "Stale rule",
            "context_payload": {},
            "constraints": [],
            "priority": JobPriorityEnum.NORMAL.value,
            "artifacts": [],
        },
        {
            "target_role_id": 5,
            "target_role_key": "reviewer",
            "summary": "Valid rule",
            "context_payload": {},
            "constraints": [],
            "priority": JobPriorityEnum.NORMAL.value,
            "artifacts": [],
        },
    ]
    completed_job = _make_completed_job(job_id=100, source_agent_id=10, routing_rules=routing_rules)

    result = await service._evaluate_routing_rules(completed_job=completed_job, actor_agent_id=10)

    # Only the valid rule's job ID is returned
    assert result == [202]


async def test_evaluate_routing_rules_skips_rule_with_missing_target_role_id() -> None:
    """When a routing rule dict is missing target_role_id, skip it."""
    repository = Mock()
    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()

    repository.create_in_savepoint = AsyncMock()
    job_event_repo.create = AsyncMock(return_value=Mock())

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    routing_rules = [
        {
            "summary": "Missing target_role_id",
            "context_payload": {},
            "constraints": [],
            "priority": JobPriorityEnum.NORMAL.value,
            "artifacts": [],
        }
    ]
    completed_job = _make_completed_job(job_id=100, source_agent_id=10, routing_rules=routing_rules)

    result = await service._evaluate_routing_rules(completed_job=completed_job, actor_agent_id=10)

    assert result == []
    repository.create_in_savepoint.assert_not_called()


# ---------------------------------------------------------------------------
# change_job_status integration with routing rules
# ---------------------------------------------------------------------------


async def test_change_job_status_completed_triggers_routing_rules_evaluation() -> None:
    """change_job_status(COMPLETED) must call _evaluate_routing_rules and add routed_job_ids to event payload."""
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_dependency_repo = Mock()
    job_dependency_repo.find_downstream_pending_job_ids = AsyncMock(return_value=[])

    # Mock the routing rule evaluation: create one routed job
    routed_job = Mock()
    routed_job.id = 200
    repository.create_in_savepoint = AsyncMock(return_value=routed_job)
    job_artifact_repo.bulk_create = AsyncMock(return_value=[])
    job_event_repo.create = AsyncMock()

    job = _make_completed_job(job_id=100, source_agent_id=10)
    job.routing_rules = [
        {
            "target_role_id": 5,
            "target_role_key": "reviewer",
            "summary": "Review",
            "context_payload": {},
            "constraints": [],
            "priority": JobPriorityEnum.NORMAL.value,
            "artifacts": [],
        }
    ]
    repository.get_by_id_for_update.return_value = job

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    await service.change_job_status(job_id=100, status=JobStatusEnum.COMPLETED, agent_id=10)

    # The TASK_COMPLETED event should include routed_job_ids
    # job_event_repo.create is called multiple times: TASK_COMPLETED, TASK_PUBLISHED, TASK_ROUTED
    assert job_event_repo.create.await_count >= 1

    # Find the TASK_COMPLETED event
    completed_event = None
    for call in job_event_repo.create.await_args_list:
        dto = call.kwargs["dto"]
        if dto.event_type == JobEventTypeEnum.TASK_COMPLETED:
            completed_event = dto
            break

    assert completed_event is not None
    assert completed_event.payload_json.get("routed_job_ids") == [200]


async def test_change_job_status_completed_without_routing_rules_does_not_create_jobs() -> None:
    """change_job_status(COMPLETED) without routing_rules must not create any jobs."""
    repository = Mock()
    repository.get_by_id_for_update = AsyncMock()
    repository.save = AsyncMock()

    job_artifact_repo = Mock()
    job_event_repo = Mock()
    job_event_repo.create = AsyncMock()
    job_dependency_repo = Mock()
    job_dependency_repo.find_downstream_pending_job_ids = AsyncMock(return_value=[])

    job = _make_completed_job(job_id=100, source_agent_id=10, routing_rules=None)
    repository.get_by_id_for_update.return_value = job

    service = _make_service(repository, job_artifact_repo, job_event_repo, job_dependency_repo)

    await service.change_job_status(job_id=100, status=JobStatusEnum.COMPLETED, agent_id=10)

    # Only the TASK_COMPLETED event, no routing events
    repository.create_in_savepoint.assert_not_called()
    assert job_event_repo.create.await_count == 1
    event_dto = job_event_repo.create.await_args.kwargs["dto"]
    assert event_dto.event_type == JobEventTypeEnum.TASK_COMPLETED
    assert "routed_job_ids" not in event_dto.payload_json
