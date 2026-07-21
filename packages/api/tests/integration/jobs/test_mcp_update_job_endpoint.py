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


async def test_update_job_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.patch("/api/v1/mcp/jobs/1", json={"context_payload": {"key": "value"}})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_update_job_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    valid_raw_token = "some-other-valid-update-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=valid_raw_token,
        role_key="update-auth-role",
        role_label="Update auth role",
        agent_label="update-auth-agent",
    )

    response = await client.patch(
        "/api/v1/mcp/jobs/1",
        json={"context_payload": {"key": "value"}},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_update_job_returns_200_and_updates_context_payload(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-update-context-payload-token"
    agent_id, role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="update-context-payload-role",
        role_label="Update context payload role",
        agent_label="update-context-payload-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="update-context-payload-source-agent",
    )

    old_context = {"ticket_id": "TCK-1"}
    new_context = {"ticket_id": "TCK-2", "extra": "data"}
    old_timestamp = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=role_id,
        status=JobStatusEnum.PUBLISHED,
        context_payload=old_context,
        constraints=["deadline:today"],
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.patch(
        f"/api/v1/mcp/jobs/{job.id}",
        json={"context_payload": new_context},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "message": f"job with job_id {job.id} updated successfully",
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.context_payload == new_context
    assert persisted_job.constraints == ["deadline:today"]
    assert persisted_job.updated_at > old_timestamp

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_UPDATED.value
    assert events[0].previous_status == JobStatusEnum.PUBLISHED
    assert events[0].current_status == JobStatusEnum.PUBLISHED
    assert events[0].actor_agent_id == agent_id
    assert "timestamp" in events[0].payload_json
    assert events[0].payload_json["changes"]["context_payload"]["old"] == old_context
    assert events[0].payload_json["changes"]["context_payload"]["new"] == new_context
    assert "constraints" not in events[0].payload_json["changes"]


async def test_update_job_returns_200_and_updates_constraints(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-update-constraints-token"
    agent_id, role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="update-constraints-role",
        role_label="Update constraints role",
        agent_label="update-constraints-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="update-constraints-source-agent",
    )

    old_constraints = ["deadline:today"]
    new_constraints = ["deadline:tomorrow", "priority:high"]
    old_context = {"key": "value"}
    old_timestamp = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=role_id,
        status=JobStatusEnum.IN_PROGRESS,
        context_payload=old_context,
        constraints=old_constraints,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.patch(
        f"/api/v1/mcp/jobs/{job.id}",
        json={"constraints": new_constraints},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "message": f"job with job_id {job.id} updated successfully",
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.constraints == new_constraints
    assert persisted_job.context_payload == old_context
    assert persisted_job.updated_at > old_timestamp

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_UPDATED.value
    assert events[0].previous_status == JobStatusEnum.IN_PROGRESS
    assert events[0].current_status == JobStatusEnum.IN_PROGRESS
    assert events[0].actor_agent_id == agent_id
    assert "timestamp" in events[0].payload_json
    assert events[0].payload_json["changes"]["constraints"]["old"] == old_constraints
    assert events[0].payload_json["changes"]["constraints"]["new"] == new_constraints
    assert "context_payload" not in events[0].payload_json["changes"]


async def test_update_job_returns_200_and_updates_both_fields(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-update-both-fields-token"
    agent_id, role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="update-both-fields-role",
        role_label="Update both fields role",
        agent_label="update-both-fields-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="update-both-fields-source-agent",
    )

    old_context = {"ticket_id": "TCK-1"}
    new_context = {"ticket_id": "TCK-2"}
    old_constraints = ["deadline:today"]
    new_constraints = ["deadline:tomorrow"]
    old_timestamp = datetime(2026, 3, 3, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=role_id,
        status=JobStatusEnum.PUBLISHED,
        context_payload=old_context,
        constraints=old_constraints,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.patch(
        f"/api/v1/mcp/jobs/{job.id}",
        json={"context_payload": new_context, "constraints": new_constraints},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": job.id,
        "message": f"job with job_id {job.id} updated successfully",
    }

    await db_session.refresh(job)
    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.context_payload == new_context
    assert persisted_job.constraints == new_constraints
    assert persisted_job.updated_at > old_timestamp

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job.id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_UPDATED.value
    assert events[0].actor_agent_id == agent_id
    assert "timestamp" in events[0].payload_json
    assert events[0].payload_json["changes"]["context_payload"]["old"] == old_context
    assert events[0].payload_json["changes"]["context_payload"]["new"] == new_context
    assert events[0].payload_json["changes"]["constraints"]["old"] == old_constraints
    assert events[0].payload_json["changes"]["constraints"]["new"] == new_constraints


async def test_update_job_returns_422_when_job_does_not_exist(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-update-missing-id-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="update-missing-id-role",
        role_label="Update missing id role",
        agent_label="update-missing-id-agent",
    )

    response = await client.patch(
        "/api/v1/mcp/jobs/999999",
        json={"context_payload": {"key": "value"}},
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


async def test_update_job_returns_422_when_both_fields_missing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-update-empty-body-token"
    agent_id, role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="update-empty-body-role",
        role_label="Update empty body role",
        agent_label="update-empty-body-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="update-empty-body-source-agent",
    )

    old_context = {"ticket_id": "TCK-1"}
    old_constraints = ["deadline:today"]
    old_timestamp = datetime(2026, 3, 4, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=role_id,
        status=JobStatusEnum.PUBLISHED,
        context_payload=old_context,
        constraints=old_constraints,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.patch(
        f"/api/v1/mcp/jobs/{job.id}",
        json={},
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422

    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.context_payload == old_context
    assert persisted_job.constraints == old_constraints
    assert persisted_job.updated_at == old_timestamp

    await _assert_no_events_for_job(db_session, job.id)
