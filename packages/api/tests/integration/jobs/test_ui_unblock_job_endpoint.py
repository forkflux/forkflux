from datetime import datetime, timezone

from forkflux_api.jobs.constants import JobEventTypeEnum, JobStatusEnum
from forkflux_api.jobs.models import HandoffJob, JobEvent
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentIdentityFactory, HandoffJobFactory, TargetRoleFactory


async def test_ui_unblock_job_returns_200_and_transitions_to_unblocked(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-unblock-role",
        role_label="UI Unblock Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-unblock-source-agent",
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-unblock-assignee-agent",
    )

    old_timestamp = datetime(2026, 2, 11, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        status=JobStatusEnum.BLOCKED,
        assignee_agent_id=assignee_agent.id,
        started_at=old_timestamp,
        claimed_at=old_timestamp,
        blocked_at=old_timestamp,
        blocked_reason="waiting on upstream dependency",
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    unblock_reason = "dependency resolved by ops team"
    response = await client.post(
        f"/api/v1/ui/jobs/{job.id}/unblock",
        json={"unblock_reason": unblock_reason},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.BLOCKED.value,
        "new_status": JobStatusEnum.UNBLOCKED.value,
        "unblock_reason": unblock_reason,
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.UNBLOCKED
    assert persisted_job.unblock_reason == unblock_reason
    assert persisted_job.unblocked_at is not None
    assert persisted_job.unblocked_at >= old_timestamp
    assert persisted_job.blocked_reason is None
    assert persisted_job.blocked_at is None
    assert persisted_job.updated_at > old_timestamp

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_UNBLOCKED.value
    assert events[0].current_status == JobStatusEnum.UNBLOCKED
    assert events[0].actor_agent_id is None
    assert events[0].payload_json["unblock_reason"] == unblock_reason
    assert "timestamp" in events[0].payload_json


async def test_ui_unblock_job_returns_422_when_job_not_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-unblock-not-blocked-role",
        role_label="UI Unblock Not Blocked Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-unblock-not-blocked-source-agent",
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-unblock-not-blocked-assignee-agent",
    )

    old_timestamp = datetime(2026, 2, 12, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=assignee_agent.id,
        started_at=old_timestamp,
        claimed_at=old_timestamp,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/ui/jobs/{job.id}/unblock",
        json={"unblock_reason": "trying to unblock an in-progress job"},
    )

    assert response.status_code == 422

    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.IN_PROGRESS
    assert persisted_job.updated_at == old_timestamp

    await _assert_no_events_for_job(db_session, job.id)


async def test_ui_unblock_job_returns_404_when_job_not_found(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/ui/jobs/999999/unblock",
        json={"unblock_reason": "non-existent job"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Handoff job not found."}


async def test_ui_unblock_job_returns_422_when_unblock_reason_missing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-unblock-missing-reason-role",
        role_label="UI Unblock Missing Reason Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-unblock-missing-reason-source-agent",
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-unblock-missing-reason-assignee-agent",
    )

    old_timestamp = datetime(2026, 2, 13, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        status=JobStatusEnum.BLOCKED,
        assignee_agent_id=assignee_agent.id,
        started_at=old_timestamp,
        claimed_at=old_timestamp,
        blocked_at=old_timestamp,
        blocked_reason="waiting on upstream dependency",
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/ui/jobs/{job.id}/unblock",
        json={},
    )

    assert response.status_code == 422

    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.BLOCKED
    assert persisted_job.updated_at == old_timestamp

    await _assert_no_events_for_job(db_session, job.id)


async def _assert_no_events_for_job(db_session: AsyncSession, job_id: int) -> None:
    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.id.asc()))
    assert list(event_rows.scalars()) == []
