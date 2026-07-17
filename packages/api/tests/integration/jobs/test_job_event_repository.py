import pytest
from forkflux_api.jobs.constants import JobEventTypeEnum, JobStatusEnum
from forkflux_api.jobs.dto import JobEventCreate
from forkflux_api.jobs.exceptions import JobEventConflictError
from forkflux_api.jobs.models import JobEvent
from forkflux_api.jobs.repositories import JobEventRepository
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentIdentityFactory, HandoffJobFactory, JobEventFactory, TargetRoleFactory


async def test_job_event_repository_init_sets_session_and_logger(db_session: AsyncSession) -> None:
    repository = JobEventRepository(session=db_session, trace_id="trace-123")

    assert repository._session is db_session
    assert repository._logger is not None


async def test_job_event_repository_create_persists_and_returns_event(db_session: AsyncSession) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-event-target-role",
        role_label="Job event target role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="job-event-source-agent",
    )
    handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    repository = JobEventRepository(session=db_session, trace_id="trace-123")
    dto = JobEventCreate(
        job_id=handoff_job.id,
        event_type=JobEventTypeEnum.TASK_PUBLISHED,
        previous_status=JobStatusEnum.PUBLISHED,
        current_status=JobStatusEnum.CLAIMED,
        actor_agent_id=source_agent.id,
        payload_json={"source": "integration-test", "reason": "claimed"},
    )

    created_event = await repository.create(dto=dto)
    fetched_event = await db_session.get(JobEvent, created_event.id)

    assert isinstance(created_event, JobEvent)
    assert created_event.id is not None
    assert created_event.job_id == handoff_job.id
    assert created_event.event_type == dto.event_type
    assert created_event.previous_status == dto.previous_status
    assert created_event.current_status == dto.current_status
    assert created_event.actor_agent_id == dto.actor_agent_id
    assert created_event.payload_json == dto.payload_json
    assert created_event.created_at is not None

    assert fetched_event is not None
    assert fetched_event.job_id == handoff_job.id
    assert fetched_event.event_type == dto.event_type
    assert fetched_event.previous_status == dto.previous_status
    assert fetched_event.current_status == dto.current_status
    assert fetched_event.actor_agent_id == dto.actor_agent_id
    assert fetched_event.payload_json == dto.payload_json


async def test_job_event_repository_create_raises_conflict_on_integrity_error(
    db_session: AsyncSession,
) -> None:
    repository = JobEventRepository(session=db_session, trace_id="trace-123")
    dto = JobEventCreate(
        job_id=999_999,
        event_type=JobEventTypeEnum.TASK_PUBLISHED,
        previous_status=JobStatusEnum.PUBLISHED,
        current_status=JobStatusEnum.CLAIMED,
        actor_agent_id=None,
        payload_json={"source": "integration-test"},
    )

    with pytest.raises(JobEventConflictError):
        await repository.create(dto=dto)


async def test_job_event_factory_creates_event_with_valid_job(db_session: AsyncSession) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-event-factory-target-role",
        role_label="Job event factory target role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="job-event-factory-source-agent",
    )
    handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    event = await JobEventFactory.create(
        db_session,
        job_id=handoff_job.id,
        actor_agent_id=source_agent.id,
    )

    assert isinstance(event, JobEvent)
    assert event.id is not None
    assert event.job_id == handoff_job.id
