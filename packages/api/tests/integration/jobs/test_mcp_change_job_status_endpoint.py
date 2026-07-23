import hashlib
from datetime import datetime, timezone

from forkflux_api.jobs.constants import JobEventTypeEnum, JobStatusEnum
from forkflux_api.jobs.models import HandoffJob, JobEvent
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentApiTokenFactory, AgentIdentityFactory, HandoffJobFactory, TargetRoleFactory


async def _create_authenticated_agent(
    db_session: AsyncSession,
    *,
    raw_token: str,
    role_key: str,
    role_label: str,
    agent_label: str,
) -> tuple[int, int]:
    role = await TargetRoleFactory.create(
        db_session,
        role_key=role_key,
        role_label=role_label,
    )
    agent = await AgentIdentityFactory.create(
        db_session,
        agent_label=agent_label,
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=agent.id,
        is_active=True,
    )
    return agent.id, role.id


async def _assert_no_events_for_job(db_session: AsyncSession, job_id: int) -> None:
    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.id.asc()))
    assert list(event_rows.scalars()) == []


async def test_change_job_status_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.post("/api/v1/mcp/jobs/1/status", json={"status": JobStatusEnum.IN_PROGRESS.value})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_change_job_status_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    valid_raw_token = "some-other-valid-change-status-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=valid_raw_token,
        role_key="change-status-auth-role",
        role_label="Change status auth role",
        agent_label="change-status-auth-agent",
    )

    response = await client.post(
        "/api/v1/mcp/jobs/1/status",
        json={"status": JobStatusEnum.IN_PROGRESS.value},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_change_job_status_returns_200_and_sets_started_at_for_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-started-token"
    assignee_id, assignee_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-started-assignee-role",
        role_label="Change status started assignee role",
        agent_label="change-status-started-assignee-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-started-source-agent",
    )

    old_timestamp = datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=assignee_role_id,
        status=JobStatusEnum.CLAIMED,
        assignee_agent_id=assignee_id,
        claimed_at=old_timestamp,
        started_at=None,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.IN_PROGRESS.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.CLAIMED.value,
        "new_status": JobStatusEnum.IN_PROGRESS.value,
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.IN_PROGRESS
    assert persisted_job.assignee_agent_id == assignee_id
    assert persisted_job.started_at is not None
    assert persisted_job.started_at >= old_timestamp
    assert persisted_job.updated_at > old_timestamp


async def test_change_job_status_returns_200_and_sets_completed_at_for_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-completed-token"
    assignee_id, assignee_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-completed-assignee-role",
        role_label="Change status completed assignee role",
        agent_label="change-status-completed-assignee-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-completed-source-agent",
    )

    old_timestamp = datetime(2026, 2, 2, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=assignee_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=assignee_id,
        started_at=old_timestamp,
        completed_at=None,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
        claimed_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.COMPLETED.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.IN_PROGRESS.value,
        "new_status": JobStatusEnum.COMPLETED.value,
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.COMPLETED
    assert persisted_job.completed_at is not None
    assert persisted_job.completed_at >= old_timestamp
    assert persisted_job.updated_at > old_timestamp


async def test_change_job_status_returns_200_and_sets_cancelled_at_for_source_agent_on_published_job(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-cancelled-token"
    source_agent_id, _source_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-cancelled-source-role",
        role_label="Change status cancelled source role",
        agent_label="change-status-cancelled-source-agent",
    )

    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="change-status-cancelled-target-role",
        role_label="Change status cancelled target role",
    )

    old_timestamp = datetime(2026, 2, 3, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role.id,
        status=JobStatusEnum.PUBLISHED,
        assignee_agent_id=None,
        cancelled_at=None,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.CANCELLED.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.PUBLISHED.value,
        "new_status": JobStatusEnum.CANCELLED.value,
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.CANCELLED
    assert persisted_job.cancelled_at is not None
    assert persisted_job.cancelled_at >= old_timestamp
    assert persisted_job.updated_at > old_timestamp


async def test_change_job_status_returns_422_when_job_does_not_exist(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-missing-id-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-missing-id-role",
        role_label="Change status missing id role",
        agent_label="change-status-missing-id-agent",
    )

    response = await client.post(
        "/api/v1/mcp/jobs/999999/status",
        json={"status": JobStatusEnum.IN_PROGRESS.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["path", "job_id"],
                "msg": "Handoff job identity is invalid.",
                "type": "handoff_job_identity.invalid",
                "input": 999999,
                "ctx": {},
            }
        ]
    }

    persisted_job = await db_session.get(HandoffJob, 999_999)
    assert persisted_job is None


async def test_change_job_status_returns_422_for_invalid_transition_and_keeps_state_unchanged(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-invalid-transition-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-invalid-transition-role",
        role_label="Change status invalid transition role",
        agent_label="change-status-invalid-transition-agent",
    )

    unchanged_updated_at = datetime(2026, 2, 4, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.PUBLISHED,
        assignee_agent_id=None,
        created_at=unchanged_updated_at,
        updated_at=unchanged_updated_at,
        published_at=unchanged_updated_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.COMPLETED.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "status"],
                "msg": "Handoff job status transition is invalid.",
                "type": "handoff_job_status.invalid",
                "input": JobStatusEnum.COMPLETED.value,
                "ctx": {},
            }
        ]
    }

    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.PUBLISHED
    assert persisted_job.updated_at == unchanged_updated_at
    assert persisted_job.completed_at is None

    await _assert_no_events_for_job(db_session, job.id)


async def test_change_job_status_returns_422_when_assignee_mismatches_and_keeps_state_unchanged(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-assignee-mismatch-token"
    caller_id, _caller_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-assignee-mismatch-caller-role",
        role_label="Change status assignee mismatch caller role",
        agent_label="change-status-assignee-mismatch-caller-agent",
    )

    assignee_role = await TargetRoleFactory.create(
        db_session,
        role_key="change-status-assignee-mismatch-assignee-role",
        role_label="Change status assignee mismatch assignee role",
    )
    real_assignee = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-assignee-mismatch-real-assignee",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-assignee-mismatch-source-agent",
    )

    unchanged_updated_at = datetime(2026, 2, 5, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=assignee_role.id,
        status=JobStatusEnum.CLAIMED,
        assignee_agent_id=real_assignee.id,
        claimed_at=unchanged_updated_at,
        created_at=unchanged_updated_at,
        updated_at=unchanged_updated_at,
        published_at=unchanged_updated_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.IN_PROGRESS.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "status"],
                "msg": "Handoff job status transition is invalid.",
                "type": "handoff_job_status.invalid",
                "input": JobStatusEnum.IN_PROGRESS.value,
                "ctx": {},
            }
        ]
    }

    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.CLAIMED
    assert persisted_job.assignee_agent_id == real_assignee.id
    assert persisted_job.started_at is None
    assert persisted_job.updated_at == unchanged_updated_at

    await _assert_no_events_for_job(db_session, job.id)
    assert caller_id != persisted_job.assignee_agent_id


async def test_change_job_status_returns_200_and_restarts_from_failed_for_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-restart-token"
    assignee_id, assignee_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-restart-assignee-role",
        role_label="Change status restart assignee role",
        agent_label="change-status-restart-assignee-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-restart-source-agent",
    )

    old_timestamp = datetime(2026, 2, 6, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=assignee_role_id,
        status=JobStatusEnum.FAILED,
        assignee_agent_id=assignee_id,
        started_at=old_timestamp,
        failed_at=old_timestamp,
        failure_reason="executor timeout",
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
        claimed_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.IN_PROGRESS.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.FAILED.value,
        "new_status": JobStatusEnum.IN_PROGRESS.value,
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.IN_PROGRESS
    assert persisted_job.assignee_agent_id == assignee_id
    assert persisted_job.started_at is not None
    assert persisted_job.started_at > old_timestamp
    assert persisted_job.failed_at is None
    assert persisted_job.failure_reason is None
    assert persisted_job.updated_at > old_timestamp

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_RESTARTED.value
    assert events[0].current_status == JobStatusEnum.IN_PROGRESS
    assert events[0].actor_agent_id == assignee_id
    assert "timestamp" in events[0].payload_json


async def test_change_job_status_returns_200_and_sets_blocked_at_and_blocked_reason_for_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-blocked-token"
    assignee_id, assignee_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-blocked-assignee-role",
        role_label="Change status blocked assignee role",
        agent_label="change-status-blocked-assignee-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-blocked-source-agent",
    )

    old_timestamp = datetime(2026, 2, 7, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=assignee_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=assignee_id,
        started_at=old_timestamp,
        claimed_at=old_timestamp,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    blocked_reason = "waiting on upstream API deployment"
    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.BLOCKED.value, "blocked_reason": blocked_reason},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.IN_PROGRESS.value,
        "new_status": JobStatusEnum.BLOCKED.value,
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.BLOCKED
    assert persisted_job.blocked_reason == blocked_reason
    assert persisted_job.blocked_at is not None
    assert persisted_job.blocked_at >= old_timestamp
    assert persisted_job.updated_at > old_timestamp

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_BLOCKED.value
    assert events[0].current_status == JobStatusEnum.BLOCKED
    assert events[0].actor_agent_id == assignee_id
    assert events[0].payload_json["blocked_reason"] == blocked_reason
    assert "timestamp" in events[0].payload_json


async def test_change_job_status_returns_200_and_unblocks_clearing_blocked_fields_for_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-unblock-token"
    assignee_id, assignee_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-unblock-assignee-role",
        role_label="Change status unblock assignee role",
        agent_label="change-status-unblock-assignee-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-unblock-source-agent",
    )

    old_timestamp = datetime(2026, 2, 8, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=assignee_role_id,
        status=JobStatusEnum.BLOCKED,
        assignee_agent_id=assignee_id,
        started_at=old_timestamp,
        claimed_at=old_timestamp,
        blocked_at=old_timestamp,
        blocked_reason="waiting on upstream dependency",
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.IN_PROGRESS.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.BLOCKED.value,
        "new_status": JobStatusEnum.IN_PROGRESS.value,
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.IN_PROGRESS
    assert persisted_job.blocked_reason is None
    assert persisted_job.blocked_at is None
    assert persisted_job.updated_at > old_timestamp

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_UNBLOCKED.value
    assert events[0].current_status == JobStatusEnum.IN_PROGRESS
    assert events[0].actor_agent_id == assignee_id
    assert "timestamp" in events[0].payload_json


async def test_change_job_status_returns_200_and_sets_unblocked_at_and_unblock_reason_for_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-unblocked-token"
    assignee_id, assignee_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-unblocked-assignee-role",
        role_label="Change status unblocked assignee role",
        agent_label="change-status-unblocked-assignee-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-unblocked-source-agent",
    )

    old_timestamp = datetime(2026, 2, 9, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=assignee_role_id,
        status=JobStatusEnum.BLOCKED,
        assignee_agent_id=assignee_id,
        started_at=old_timestamp,
        claimed_at=old_timestamp,
        blocked_at=old_timestamp,
        blocked_reason="waiting on upstream dependency",
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    unblock_reason = "upstream dependency deployed successfully"
    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.UNBLOCKED.value, "unblock_reason": unblock_reason},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.BLOCKED.value,
        "new_status": JobStatusEnum.UNBLOCKED.value,
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
    assert events[0].actor_agent_id == assignee_id
    assert events[0].payload_json["unblock_reason"] == unblock_reason
    assert "timestamp" in events[0].payload_json


async def test_change_job_status_returns_200_and_resumes_from_unblocked_for_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-change-status-resume-unblocked-token"
    assignee_id, assignee_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="change-status-resume-unblocked-assignee-role",
        role_label="Change status resume unblocked assignee role",
        agent_label="change-status-resume-unblocked-assignee-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="change-status-resume-unblocked-source-agent",
    )

    old_timestamp = datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=assignee_role_id,
        status=JobStatusEnum.UNBLOCKED,
        assignee_agent_id=assignee_id,
        started_at=old_timestamp,
        claimed_at=old_timestamp,
        unblocked_at=old_timestamp,
        unblock_reason="dependency resolved",
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/status",
        json={"status": JobStatusEnum.IN_PROGRESS.value},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "previous_status": JobStatusEnum.UNBLOCKED.value,
        "new_status": JobStatusEnum.IN_PROGRESS.value,
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.IN_PROGRESS
    assert persisted_job.unblock_reason is None
    assert persisted_job.unblocked_at is None
    assert persisted_job.started_at is not None
    assert persisted_job.started_at > old_timestamp
    assert persisted_job.updated_at > old_timestamp

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_STARTED.value
    assert events[0].current_status == JobStatusEnum.IN_PROGRESS
    assert events[0].actor_agent_id == assignee_id
    assert "timestamp" in events[0].payload_json
