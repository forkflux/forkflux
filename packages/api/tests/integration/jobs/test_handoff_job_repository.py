import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.models import AgentIdentity, TargetRole
from src.jobs.constants import JobPriorityEnum, JobStatusEnum
from src.jobs.dto import HandoffJobCreate
from src.jobs.exceptions import HandoffJobConflictError, HandoffJobNotFoundError
from src.jobs.models import HandoffJob
from src.jobs.repositories import HandoffJobRepository
from tests.factories import AgentIdentityFactory, HandoffJobFactory, TargetRoleFactory


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
        constraints=[{"type": "deadline", "value": "today"}],
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

    assert fetched_job.id == created_job.id
    assert fetched_job.summary == created_job.summary
    assert fetched_job.source_agent_id == source_agent.id
    assert fetched_job.target_role_id == target_role.id


async def test_handoff_job_repository_get_raises_not_found_for_missing_job_id(db_session: AsyncSession) -> None:
    repository = HandoffJobRepository(session=db_session, trace_id="trace-123")

    with pytest.raises(HandoffJobNotFoundError):
        await repository.get(job_id=999_999)
