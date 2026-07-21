import hashlib
from datetime import datetime, timezone

from forkflux_api.jobs.constants import JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.models import HandoffJob, JobEvent
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import (
    AgentApiTokenFactory,
    AgentIdentityFactory,
    AgentIdentityRoleFactory,
    HandoffJobFactory,
    TargetRoleFactory,
)


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
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=agent.id,
        target_role_id=role.id,
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


async def test_claim_job_returns_201_and_job_with_artifacts_response_and_persists_status_and_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-job-token"
    claimant_id, claimant_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-job-claimant-role",
        role_label="Claim job claimant role",
        agent_label="claim-job-claimant-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-job-source-agent",
    )

    old_timestamp = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=claimant_role_id,
        status=JobStatusEnum.PUBLISHED,
        assignee_agent_id=None,
        claimed_at=None,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == job.id
    assert body["parent_job_id"] == job.parent_job_id
    assert body["summary"] == job.summary
    assert body["context_payload"] == job.context_payload
    assert body["status"] == JobStatusEnum.IN_PROGRESS.value
    assert body["priority"] == JobPriorityEnum(job.priority).value
    assert body["source_agent_label"] == source_agent.agent_label
    assert body["assignee_agent_label"] == "claim-job-claimant-agent"
    assert body["target_role_key"] == "claim-job-claimant-role"
    assert body["constraints"] == job.constraints
    assert body["artifacts"] == []
    assert body["failure_reason"] is None
    assert body["published_at"] == job.published_at.isoformat().replace("+00:00", "Z")
    assert body["claimed_at"] is not None
    assert body["started_at"] is not None
    assert body["completed_at"] is None
    assert body["failed_at"] is None
    assert body["cancelled_at"] is None
    assert body["expires_at"] is None
    assert body["created_at"] == job.created_at.isoformat().replace("+00:00", "Z")

    await db_session.refresh(job)
    claimed_job = await db_session.get(HandoffJob, job.id)
    assert claimed_job is not None
    assert claimed_job.status == JobStatusEnum.IN_PROGRESS
    assert claimed_job.assignee_agent_id == claimant_id
    assert claimed_job.claimed_at is not None
    assert claimed_job.claimed_at >= old_timestamp
    assert claimed_job.started_at is not None
    assert claimed_job.started_at >= old_timestamp
    assert claimed_job.updated_at > old_timestamp
    assert body["updated_at"] == claimed_job.updated_at.isoformat().replace("+00:00", "Z")

    await _assert_no_events_for_job(db_session, job.id)


async def test_claim_job_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.post("/api/v1/mcp/jobs/1/claim")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_claim_job_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    valid_raw_token = "some-other-valid-claim-job-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=valid_raw_token,
        role_key="claim-job-auth-role",
        role_label="Claim job auth role",
        agent_label="claim-job-auth-agent",
    )

    response = await client.post(
        "/api/v1/mcp/jobs/1/claim",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_claim_job_returns_422_when_job_does_not_exist(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-job-missing-id-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-job-missing-id-role",
        role_label="Claim job missing id role",
        agent_label="claim-job-missing-id-agent",
    )

    response = await client.post(
        "/api/v1/mcp/jobs/999999/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["path", "job_id"],
                "msg": "Handoff job claim is invalid: Handoff job not found.",
                "type": "handoff_job_claim.invalid",
                "input": 999999,
                "ctx": {},
            }
        ]
    }

    persisted_job = await db_session.get(HandoffJob, 999_999)
    assert persisted_job is None


async def test_claim_job_returns_422_when_job_status_is_not_published(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-job-status-token"
    claimant_id, claimant_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-job-status-claimant-role",
        role_label="Claim job status claimant role",
        agent_label="claim-job-status-claimant-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-job-status-source-agent",
    )

    unchanged_updated_at = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=claimant_role_id,
        status=JobStatusEnum.CLAIMED,
        assignee_agent_id=None,
        updated_at=unchanged_updated_at,
        created_at=unchanged_updated_at,
        published_at=unchanged_updated_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["path", "job_id"],
                "msg": "Handoff job claim is invalid: Handoff job conflicts with existing data constraints.",
                "type": "handoff_job_claim.invalid",
                "input": job.id,
                "ctx": {},
            }
        ]
    }

    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.CLAIMED
    assert persisted_job.assignee_agent_id is None
    assert persisted_job.updated_at == unchanged_updated_at

    await _assert_no_events_for_job(db_session, job.id)
    assert claimant_id != persisted_job.source_agent_id


async def test_claim_job_returns_422_when_claimant_role_does_not_match_target_role(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-job-role-mismatch-token"
    claimant_id, _claimant_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-job-role-mismatch-claimant-role",
        role_label="Claim job role mismatch claimant role",
        agent_label="claim-job-role-mismatch-claimant-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-job-role-mismatch-source-agent",
    )
    real_target_role = await TargetRoleFactory.create(
        db_session,
        role_key="claim-job-role-mismatch-target-role",
        role_label="Claim job role mismatch target role",
    )

    unchanged_updated_at = datetime(2026, 1, 3, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=real_target_role.id,
        status=JobStatusEnum.PUBLISHED,
        assignee_agent_id=None,
        updated_at=unchanged_updated_at,
        created_at=unchanged_updated_at,
        published_at=unchanged_updated_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["path", "job_id"],
                "msg": "Handoff job claim is invalid: Handoff job conflicts with existing data constraints.",
                "type": "handoff_job_claim.invalid",
                "input": job.id,
                "ctx": {},
            }
        ]
    }

    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.PUBLISHED
    assert persisted_job.assignee_agent_id is None
    assert persisted_job.updated_at == unchanged_updated_at

    await _assert_no_events_for_job(db_session, job.id)
    assert claimant_id != persisted_job.source_agent_id


async def test_claim_job_returns_422_when_job_is_already_assigned(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-job-assigned-token"
    claimant_id, claimant_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-job-assigned-claimant-role",
        role_label="Claim job assigned claimant role",
        agent_label="claim-job-assigned-claimant-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-job-assigned-source-agent",
    )
    existing_assignee = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-job-assigned-existing-assignee",
    )

    unchanged_updated_at = datetime(2026, 1, 4, 9, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=claimant_role_id,
        status=JobStatusEnum.PUBLISHED,
        assignee_agent_id=existing_assignee.id,
        updated_at=unchanged_updated_at,
        created_at=unchanged_updated_at,
        published_at=unchanged_updated_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{job.id}/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["path", "job_id"],
                "msg": "Handoff job claim is invalid: Handoff job conflicts with existing data constraints.",
                "type": "handoff_job_claim.invalid",
                "input": job.id,
                "ctx": {},
            }
        ]
    }

    persisted_job = await db_session.get(HandoffJob, job.id)
    assert persisted_job is not None
    assert persisted_job.status == JobStatusEnum.PUBLISHED
    assert persisted_job.assignee_agent_id == existing_assignee.id
    assert persisted_job.updated_at == unchanged_updated_at

    await _assert_no_events_for_job(db_session, job.id)
    assert claimant_id != persisted_job.assignee_agent_id
