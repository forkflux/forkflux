from datetime import datetime, timedelta, timezone

import pytest
from forkflux_api.agents.models import AgentIdentity, TargetRole
from forkflux_api.jobs.constants import JobListOrderEnum, JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.dto import HandoffJobCreate, HandoffJobFilterParams
from forkflux_api.jobs.exceptions import HandoffJobConflictError, HandoffJobHasChildrenError, HandoffJobNotFoundError
from forkflux_api.jobs.models import HandoffJob, JobArtifact, JobEvent
from forkflux_api.jobs.repositories import HandoffJobRepository
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import (
    AgentApiTokenFactory,
    AgentIdentityFactory,
    HandoffJobFactory,
    JobArtifactFactory,
    JobEventFactory,
    TargetRoleFactory,
)


async def test_handoff_job_repository_init_sets_session_and_logger(db_session: AsyncSession) -> None:
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    assert repository._session is db_session
    assert repository._logger is not None


async def test_handoff_job_repository_create_persists_and_applies_defaults(db_session: AsyncSession) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-target-role",
        role_label="Handoff target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-source-role",
        role_label="Handoff source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-source-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")
    dto = HandoffJobCreate(
        parent_job_id=None,
        summary="Summarize and prepare handoff",
        context_payload={"ticket_id": "TCK-42", "scope": "billing"},
        priority=JobPriorityEnum.HIGH,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        constraints=["deadline:today"],
    )

    created_job = await repository.create(dto=dto)
    fetched_job = await db_session.get(HandoffJob, created_job.id)

    assert isinstance(created_job, HandoffJob)
    assert created_job.id is not None
    assert created_job.parent_job_id is None
    assert created_job.summary == dto.summary
    assert created_job.context_payload == dto.context_payload
    assert created_job.priority == JobPriorityEnum.HIGH.value
    assert created_job.status == JobStatusEnum.PUBLISHED
    assert created_job.source_agent_id == source_agent.id
    assert created_job.target_role_id == target_role.id
    assert created_job.assignee_agent_id is None
    assert created_job.constraints == dto.constraints
    assert created_job.failure_reason is None
    assert created_job.claimed_at is None
    assert created_job.started_at is None
    assert created_job.completed_at is None
    assert created_job.failed_at is None
    assert created_job.cancelled_at is None
    assert created_job.expires_at is None
    assert created_job.published_at is not None
    assert created_job.created_at is not None
    assert created_job.updated_at is not None
    assert created_job.published_at == created_job.created_at
    assert created_job.updated_at == created_job.created_at

    assert fetched_job is not None
    assert fetched_job.priority == JobPriorityEnum.HIGH.value
    assert fetched_job.status == JobStatusEnum.PUBLISHED
    assert fetched_job.source_agent_id == source_agent.id
    assert fetched_job.target_role_id == target_role.id

    persisted_source_agent = await db_session.get(AgentIdentity, source_agent.id)
    persisted_target_role = await db_session.get(TargetRole, target_role.id)
    assert persisted_source_agent is not None
    assert persisted_target_role is not None


async def test_handoff_job_factory_uses_database_identity_sequence(db_session: AsyncSession) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-sequence-target-role",
        role_label="Handoff sequence target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-sequence-source-role",
        role_label="Handoff sequence source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-sequence-source-agent",
        role_id=source_role.id,
    )

    created_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    assert created_job.id == 1


async def test_handoff_job_repository_create_raises_conflict_on_invalid_source_agent_id_and_session_remains_usable(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-conflict-target-role-invalid-source",
        role_label="Handoff conflict target role invalid source",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-conflict-source-role-invalid-source",
        role_label="Handoff conflict source role invalid source",
    )
    valid_source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-valid-source-agent-after-rollback",
        role_id=source_role.id,
    )
    valid_source_agent_id = valid_source_agent.id
    target_role_id = target_role.id
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    invalid_source_dto = HandoffJobCreate(
        parent_job_id=None,
        summary="Should fail due to invalid source agent",
        context_payload={"ticket_id": "TCK-500", "scope": "billing"},
        priority=JobPriorityEnum.HIGH,
        source_agent_id=999_999,
        target_role_id=target_role_id,
        constraints=[],
    )

    with pytest.raises(HandoffJobConflictError):
        await repository.create(dto=invalid_source_dto)

    valid_dto = HandoffJobCreate(
        parent_job_id=None,
        summary="Should succeed after rollback",
        context_payload={"ticket_id": "TCK-501", "scope": "billing"},
        priority=JobPriorityEnum.HIGH,
        source_agent_id=valid_source_agent_id,
        target_role_id=target_role_id,
        constraints=[],
    )
    created_job = await repository.create(dto=valid_dto)

    assert created_job.id is not None
    assert created_job.source_agent_id == valid_source_agent_id
    assert created_job.target_role_id == target_role_id


async def test_handoff_job_repository_create_raises_conflict_on_invalid_target_role_id_and_session_remains_usable(
    db_session: AsyncSession,
) -> None:
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-conflict-source-role-invalid-target",
        role_label="Handoff conflict source role invalid target",
    )
    valid_target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-valid-target-role-after-rollback",
        role_label="Handoff valid target role after rollback",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-source-agent-invalid-target",
        role_id=source_role.id,
    )
    source_agent_id = source_agent.id
    valid_target_role_id = valid_target_role.id
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    invalid_target_dto = HandoffJobCreate(
        parent_job_id=None,
        summary="Should fail due to invalid target role",
        context_payload={"ticket_id": "TCK-600", "scope": "support"},
        priority=JobPriorityEnum.HIGH,
        source_agent_id=source_agent_id,
        target_role_id=999_999,
        constraints=[],
    )

    with pytest.raises(HandoffJobConflictError):
        await repository.create(dto=invalid_target_dto)

    valid_dto = HandoffJobCreate(
        parent_job_id=None,
        summary="Should succeed after rollback",
        context_payload={"ticket_id": "TCK-601", "scope": "support"},
        priority=JobPriorityEnum.HIGH,
        source_agent_id=source_agent_id,
        target_role_id=valid_target_role_id,
        constraints=[],
    )
    created_job = await repository.create(dto=valid_dto)

    assert created_job.id is not None
    assert created_job.source_agent_id == source_agent_id
    assert created_job.target_role_id == valid_target_role_id


async def test_handoff_job_repository_save_persists_updated_job_and_returns_updated_object(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-save-target-role",
        role_label="Handoff save target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-save-source-role",
        role_label="Handoff save source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-save-source-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")
    handoff_job = await HandoffJobFactory.create(
        db_session,
        summary="Before save",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        status=JobStatusEnum.PUBLISHED,
    )
    original_updated_at = handoff_job.updated_at

    handoff_job.summary = "After save"
    handoff_job.status = JobStatusEnum.CLAIMED
    handoff_job.failure_reason = "waiting for assignee"
    saved_job = await repository.save(job=handoff_job)

    fetched_job = await db_session.get(HandoffJob, handoff_job.id)

    assert isinstance(saved_job, HandoffJob)
    assert saved_job.id == handoff_job.id
    assert saved_job.summary == "After save"
    assert saved_job.status == JobStatusEnum.CLAIMED
    assert saved_job.failure_reason == "waiting for assignee"
    assert saved_job.updated_at > original_updated_at

    assert fetched_job is not None
    assert fetched_job.summary == "After save"
    assert fetched_job.status == JobStatusEnum.CLAIMED
    assert fetched_job.failure_reason == "waiting for assignee"
    assert fetched_job.updated_at == saved_job.updated_at


async def test_handoff_job_repository_get_returns_job_by_id(db_session: AsyncSession) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-get-target-role",
        role_label="Handoff get target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-get-source-role",
        role_label="Handoff get source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-get-source-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")
    created_job = await HandoffJobFactory.create(
        db_session,
        summary="Get handoff job by id",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    fetched_job = await repository.get(job_id=created_job.id)

    assert fetched_job.job_details.id == created_job.id
    assert fetched_job.job_details.summary == created_job.summary
    assert fetched_job.job_details.source_agent_id == source_agent.id
    assert fetched_job.job_details.target_role_id == target_role.id
    assert fetched_job.target_role_key == target_role.role_key
    assert fetched_job.source_agent_label == source_agent.agent_label
    assert fetched_job.assignee_agent_label is None


async def test_handoff_job_repository_get_raises_not_found_for_missing_job_id(db_session: AsyncSession) -> None:
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    with pytest.raises(HandoffJobNotFoundError):
        await repository.get(job_id=999_999)


async def test_handoff_job_repository_get_by_id_for_update_returns_job_by_id(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-get-for-update-target-role",
        role_label="Handoff get for update target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-get-for-update-source-role",
        role_label="Handoff get for update source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-get-for-update-source-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")
    created_job = await HandoffJobFactory.create(
        db_session,
        summary="Get handoff job by id for update",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    fetched_job = await repository.get_by_id_for_update(job_id=created_job.id)

    assert isinstance(fetched_job, HandoffJob)
    assert fetched_job.id == created_job.id
    assert fetched_job.summary == created_job.summary
    assert fetched_job.source_agent_id == source_agent.id
    assert fetched_job.target_role_id == target_role.id


async def test_handoff_job_repository_get_by_id_for_update_raises_not_found_for_missing_job_id(
    db_session: AsyncSession,
) -> None:
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    with pytest.raises(HandoffJobNotFoundError):
        await repository.get_by_id_for_update(job_id=999_999)


async def test_handoff_job_repository_list_returns_items_with_target_role_key_and_created_at_asc(
    db_session: AsyncSession,
) -> None:
    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-list-reviewer",
        role_label="Handoff list reviewer",
    )
    operator_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-list-operator",
        role_label="Handoff list operator",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-list-source",
        role_label="Handoff list source",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-list-source-agent",
        role_id=source_role.id,
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-list-assignee-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    oldest_job = await HandoffJobFactory.create(
        db_session,
        summary="Oldest",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    _middle_job = await HandoffJobFactory.create(
        db_session,
        summary="Middle",
        status=JobStatusEnum.CLAIMED,
        source_agent_id=source_agent.id,
        target_role_id=operator_role.id,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    newest_job = await HandoffJobFactory.create(
        db_session,
        summary="Newest",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        assignee_agent_id=assignee_agent.id,
        created_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        published_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
    )

    all_items = await repository.list(
        filter_params=HandoffJobFilterParams(
            limit=200,
            statuses=[JobStatusEnum.PUBLISHED],
            target_role_id=None,
            order=[JobListOrderEnum.CREATED_AT_ASC],
        )
    )

    assert [item.job_details.id for item in all_items] == [oldest_job.id, newest_job.id]
    assert [item.target_role_key for item in all_items] == [
        reviewer_role.role_key,
        reviewer_role.role_key,
    ]
    assert [item.source_agent_label for item in all_items] == [
        source_agent.agent_label,
        source_agent.agent_label,
    ]
    assert [item.assignee_agent_label for item in all_items] == [None, assignee_agent.agent_label]


async def test_handoff_job_repository_list_filters_by_status_and_target_role_key(db_session: AsyncSession) -> None:
    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-list-status-reviewer",
        role_label="Handoff list status reviewer",
    )
    operator_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-list-status-operator",
        role_label="Handoff list status operator",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-list-status-source",
        role_label="Handoff list status source",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-list-status-source-agent",
        role_id=source_role.id,
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-list-status-assignee-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    matching_job = await HandoffJobFactory.create(
        db_session,
        summary="Matching",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        assignee_agent_id=assignee_agent.id,
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Non matching status",
        status=JobStatusEnum.CLAIMED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Non matching role",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=operator_role.id,
    )

    filtered_items = await repository.list(
        filter_params=HandoffJobFilterParams(
            limit=200,
            statuses=[JobStatusEnum.PUBLISHED],
            target_role_id=reviewer_role.id,
            order=[JobListOrderEnum.CREATED_AT_ASC],
        )
    )

    assert len(filtered_items) == 1
    assert filtered_items[0].job_details.id == matching_job.id
    assert filtered_items[0].target_role_key == reviewer_role.role_key
    assert filtered_items[0].source_agent_label == source_agent.agent_label
    assert filtered_items[0].assignee_agent_label == assignee_agent.agent_label


async def test_handoff_job_repository_list_applies_limit(db_session: AsyncSession) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-list-limit-role",
        role_label="Handoff list limit role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-list-limit-source",
        role_label="Handoff list limit source",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-list-limit-source-agent",
        role_id=source_role.id,
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-list-limit-assignee-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    first_job = None
    base_dt = datetime(2026, 2, 1, tzinfo=timezone.utc)
    for day_offset in range(51):
        current_dt = base_dt + timedelta(days=day_offset)
        created_job = await HandoffJobFactory.create(
            db_session,
            source_agent_id=source_agent.id,
            target_role_id=target_role.id,
            assignee_agent_id=assignee_agent.id,
            created_at=current_dt,
            updated_at=current_dt,
            published_at=current_dt,
        )
        if day_offset == 0:
            first_job = created_job

    items = await repository.list(
        filter_params=HandoffJobFilterParams(
            limit=50,
            statuses=[JobStatusEnum.PUBLISHED],
            target_role_id=None,
            order=[JobListOrderEnum.CREATED_AT_ASC],
        )
    )

    assert first_job is not None
    assert len(items) == 50
    assert items[0].job_details.id == first_job.id
    assert items[0].target_role_key == target_role.role_key
    assert items[0].source_agent_label == source_agent.agent_label
    assert items[0].assignee_agent_label == assignee_agent.agent_label


async def test_handoff_job_repository_delete_removes_job_and_cascades_related_rows(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-delete-target-role",
        role_label="Handoff delete target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-delete-source-role",
        role_label="Handoff delete source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-delete-source-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    artifact = await JobArtifactFactory.create(
        db_session,
        job_id=job.id,
    )
    event = await JobEventFactory.create(
        db_session,
        job_id=job.id,
        actor_agent_id=source_agent.id,
    )

    await repository.delete(job_id=job.id)

    deleted_job = await db_session.get(HandoffJob, job.id)
    deleted_artifact_id = await db_session.get(JobArtifact, artifact.id, populate_existing=True)
    deleted_event_id = await db_session.get(JobEvent, event.id, populate_existing=True)

    assert deleted_job is None
    assert deleted_artifact_id is None
    assert deleted_event_id is None


async def test_handoff_job_repository_delete_raises_has_children_when_child_jobs_exist(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-delete-children-target-role",
        role_label="Handoff delete children target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-delete-children-source-role",
        role_label="Handoff delete children source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-delete-children-source-agent",
        role_id=source_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")
    parent_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    child_job = await HandoffJobFactory.create(
        db_session,
        parent_job_id=parent_job.id,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    with pytest.raises(HandoffJobHasChildrenError):
        await repository.delete(job_id=parent_job.id)

    persisted_parent_job = await db_session.get(HandoffJob, parent_job.id)
    persisted_child_job = await db_session.get(HandoffJob, child_job.id)

    assert persisted_parent_job is not None
    assert persisted_child_job is not None


async def test_handoff_job_repository_stats_returns_zeroed_metrics_for_empty_database(
    db_session: AsyncSession,
) -> None:
    repository = HandoffJobRepository(session=db_session, trace_id="trace-stats-empty")

    result = await repository.stats()

    assert result.window_hours == 24
    assert result.stuck_minutes == 60
    assert result.total_jobs == 0
    assert result.active_agents == 0
    assert result.stuck_jobs == 0
    assert result.total_handoffs == 0
    assert result.waiting_jobs_by_role == []
    assert result.published_to_claimed_pairs == []
    assert result.published_to_resolution_pairs == []
    assert result.status_counts[JobStatusEnum.PUBLISHED] == 0
    assert result.status_counts[JobStatusEnum.CLAIMED] == 0
    assert result.status_counts[JobStatusEnum.IN_PROGRESS] == 0
    assert result.status_counts[JobStatusEnum.COMPLETED] == 0
    assert result.status_counts[JobStatusEnum.FAILED] == 0
    assert result.status_counts[JobStatusEnum.CANCELLED] == 0
    assert result.all_time_status_counts[JobStatusEnum.PUBLISHED] == 0
    assert result.all_time_status_counts[JobStatusEnum.CLAIMED] == 0
    assert result.all_time_status_counts[JobStatusEnum.IN_PROGRESS] == 0
    assert result.all_time_status_counts[JobStatusEnum.COMPLETED] == 0
    assert result.all_time_status_counts[JobStatusEnum.FAILED] == 0
    assert result.all_time_status_counts[JobStatusEnum.CANCELLED] == 0


async def test_handoff_job_repository_stats_computes_status_distribution_rates_and_medians(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-stats-target-role",
        role_label="Handoff stats target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="handoff-stats-source-role",
        role_label="Handoff stats source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-stats-source-agent",
        role_id=source_role.id,
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-stats-assignee-agent",
        role_id=target_role.id,
    )
    stale_assignee = await AgentIdentityFactory.create(
        db_session,
        agent_label="handoff-stats-stale-assignee",
        role_id=target_role.id,
    )
    repository = HandoffJobRepository(session=db_session, trace_id="trace-stats-aggregate")

    recent = datetime.now(timezone.utc)
    base = recent - timedelta(hours=6)

    await AgentApiTokenFactory.create(
        db_session,
        agent_id=assignee_agent.id,
        last_used_at=recent - timedelta(minutes=30),
    )
    await AgentApiTokenFactory.create(
        db_session,
        agent_id=source_agent.id,
        last_used_at=recent - timedelta(hours=23),
    )
    await AgentApiTokenFactory.create(
        db_session,
        agent_id=stale_assignee.id,
        last_used_at=recent - timedelta(hours=26),
    )

    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=None,
        status=JobStatusEnum.PUBLISHED,
        published_at=base,
        claimed_at=None,
        completed_at=None,
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=assignee_agent.id,
        status=JobStatusEnum.CLAIMED,
        published_at=base,
        claimed_at=base + timedelta(minutes=15),
        completed_at=None,
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=assignee_agent.id,
        status=JobStatusEnum.IN_PROGRESS,
        published_at=base,
        claimed_at=base + timedelta(minutes=12),
        started_at=base + timedelta(minutes=13),
        completed_at=None,
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=assignee_agent.id,
        status=JobStatusEnum.COMPLETED,
        published_at=base,
        claimed_at=base + timedelta(minutes=10),
        completed_at=base + timedelta(minutes=40),
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=assignee_agent.id,
        status=JobStatusEnum.COMPLETED,
        published_at=base,
        claimed_at=base + timedelta(minutes=20),
        completed_at=base + timedelta(minutes=80),
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=assignee_agent.id,
        status=JobStatusEnum.COMPLETED,
        published_at=base + timedelta(minutes=60),
        claimed_at=base + timedelta(minutes=90),
        completed_at=base + timedelta(minutes=55),
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=assignee_agent.id,
        status=JobStatusEnum.FAILED,
        published_at=base,
        claimed_at=None,
        failed_at=base + timedelta(minutes=30),
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=None,
        status=JobStatusEnum.CANCELLED,
        published_at=base,
        claimed_at=None,
        cancelled_at=base + timedelta(minutes=5),
    )

    # stale active job outside window should still be counted as stuck
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=stale_assignee.id,
        status=JobStatusEnum.IN_PROGRESS,
        published_at=recent - timedelta(hours=30),
        claimed_at=recent - timedelta(hours=29),
        started_at=recent - timedelta(hours=29),
        created_at=recent - timedelta(hours=30),
        updated_at=recent - timedelta(hours=2),
    )

    # recent waiting jobs for role bottleneck
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        status=JobStatusEnum.PUBLISHED,
        published_at=recent - timedelta(minutes=40),
        created_at=recent - timedelta(minutes=40),
        updated_at=recent - timedelta(minutes=40),
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        status=JobStatusEnum.PUBLISHED,
        published_at=recent - timedelta(minutes=20),
        created_at=recent - timedelta(minutes=20),
        updated_at=recent - timedelta(minutes=20),
    )

    result = await repository.stats(window_hours=24, stuck_minutes=60)

    assert result.window_hours == 24
    assert result.stuck_minutes == 60
    assert result.total_jobs == 10
    assert result.status_counts[JobStatusEnum.PUBLISHED] == 3
    assert result.status_counts[JobStatusEnum.CLAIMED] == 1
    assert result.status_counts[JobStatusEnum.IN_PROGRESS] == 1
    assert result.status_counts[JobStatusEnum.COMPLETED] == 3
    assert result.status_counts[JobStatusEnum.FAILED] == 1
    assert result.status_counts[JobStatusEnum.CANCELLED] == 1
    assert result.all_time_status_counts[JobStatusEnum.IN_PROGRESS] == 2
    assert result.active_agents == 2
    assert result.stuck_jobs == 1
    assert result.total_handoffs == 3
    assert result.waiting_jobs_by_role[0] == (target_role.role_key, 3)
    assert len(result.published_to_claimed_pairs) == 5
    assert len(result.published_to_resolution_pairs) == 5
    assert (base, base + timedelta(minutes=15)) in result.published_to_claimed_pairs
    assert (base + timedelta(minutes=60), base + timedelta(minutes=55)) in result.published_to_resolution_pairs
