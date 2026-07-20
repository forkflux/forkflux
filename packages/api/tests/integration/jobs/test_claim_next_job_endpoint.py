import hashlib
from datetime import datetime, timedelta, timezone

from forkflux_api.jobs.constants import JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.models import HandoffJob
from httpx import AsyncClient
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


async def test_claim_next_job_returns_201_and_claims_published_job(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-next-job-token"
    claimant_id, claimant_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-next-job-claimant-role",
        role_label="Claim next job claimant role",
        agent_label="claim-next-job-claimant-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-next-job-source-agent",
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
        "/api/v1/mcp/jobs/claim-next",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"target_role_key": "claim-next-job-claimant-role"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == job.id
    assert body["status"] == JobStatusEnum.IN_PROGRESS.value
    assert body["assignee_agent_label"] == "claim-next-job-claimant-agent"
    assert body["target_role_key"] == "claim-next-job-claimant-role"
    assert body["claimed_at"] is not None
    assert body["started_at"] is not None

    await db_session.refresh(job)
    claimed_job = await db_session.get(HandoffJob, job.id)
    assert claimed_job is not None
    assert claimed_job.status == JobStatusEnum.IN_PROGRESS
    assert claimed_job.assignee_agent_id == claimant_id
    assert claimed_job.claimed_at is not None
    assert claimed_job.started_at is not None


async def test_claim_next_job_selects_highest_priority_then_oldest(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-next-job-priority-token"
    claimant_id, claimant_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-next-job-priority-role",
        role_label="Claim next job priority role",
        agent_label="claim-next-job-priority-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-next-job-priority-source-agent",
    )

    base_dt = datetime(2026, 2, 1, tzinfo=timezone.utc)

    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=claimant_role_id,
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.NORMAL.value,
        assignee_agent_id=None,
        created_at=base_dt,
        updated_at=base_dt,
        published_at=base_dt,
    )

    expected_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=claimant_role_id,
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.URGENT.value,
        assignee_agent_id=None,
        created_at=base_dt + timedelta(days=1),
        updated_at=base_dt + timedelta(days=1),
        published_at=base_dt + timedelta(days=1),
    )

    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=claimant_role_id,
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.URGENT.value,
        assignee_agent_id=None,
        created_at=base_dt + timedelta(days=2),
        updated_at=base_dt + timedelta(days=2),
        published_at=base_dt + timedelta(days=2),
    )

    response = await client.post(
        "/api/v1/mcp/jobs/claim-next",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"target_role_key": "claim-next-job-priority-role"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == expected_job.id
    assert body["priority"] == JobPriorityEnum.URGENT.value

    await db_session.refresh(expected_job)
    claimed_job = await db_session.get(HandoffJob, expected_job.id)
    assert claimed_job is not None
    assert claimed_job.assignee_agent_id == claimant_id


async def test_claim_next_job_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/mcp/jobs/claim-next",
        json={"target_role_key": "some-role"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_claim_next_job_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    valid_raw_token = "some-other-valid-claim-next-job-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=valid_raw_token,
        role_key="claim-next-job-auth-role",
        role_label="Claim next job auth role",
        agent_label="claim-next-job-auth-agent",
    )

    response = await client.post(
        "/api/v1/mcp/jobs/claim-next",
        headers={"Authorization": "Bearer invalid-token"},
        json={"target_role_key": "claim-next-job-auth-role"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_claim_next_job_returns_422_when_target_role_key_is_invalid(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-next-job-invalid-role-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-next-job-invalid-role-claimant-role",
        role_label="Claim next job invalid role claimant role",
        agent_label="claim-next-job-invalid-role-agent",
    )

    response = await client.post(
        "/api/v1/mcp/jobs/claim-next",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"target_role_key": "non-existent-role-key"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "target_role_key"],
                "msg": "Target role is invalid.",
                "type": "target_role.invalid",
                "input": "non-existent-role-key",
                "ctx": {},
            }
        ]
    }


async def test_claim_next_job_returns_404_when_no_published_jobs_available(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-next-job-no-jobs-token"
    _, _ = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-next-job-no-jobs-role",
        role_label="Claim next job no jobs role",
        agent_label="claim-next-job-no-jobs-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-next-job-no-jobs-source-agent",
    )
    role = await TargetRoleFactory.create(
        db_session,
        role_key="claim-next-job-no-jobs-target-role",
        role_label="Claim next job no jobs target role",
    )

    old_timestamp = datetime(2026, 3, 1, tzinfo=timezone.utc)
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=role.id,
        status=JobStatusEnum.CLAIMED,
        assignee_agent_id=None,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        "/api/v1/mcp/jobs/claim-next",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"target_role_key": "claim-next-job-no-jobs-target-role"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "No published jobs available for the given target role."}


async def test_claim_next_job_returns_422_when_claimant_role_does_not_match_target_role(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-claim-next-job-role-mismatch-token"
    claimant_id, _ = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="claim-next-job-role-mismatch-claimant-role",
        role_label="Claim next job role mismatch claimant role",
        agent_label="claim-next-job-role-mismatch-claimant-agent",
    )

    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="claim-next-job-role-mismatch-source-agent",
    )
    real_target_role = await TargetRoleFactory.create(
        db_session,
        role_key="claim-next-job-role-mismatch-target-role",
        role_label="Claim next job role mismatch target role",
    )

    old_timestamp = datetime(2026, 4, 1, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=real_target_role.id,
        status=JobStatusEnum.PUBLISHED,
        assignee_agent_id=None,
        created_at=old_timestamp,
        updated_at=old_timestamp,
        published_at=old_timestamp,
    )

    response = await client.post(
        "/api/v1/mcp/jobs/claim-next",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"target_role_key": "claim-next-job-role-mismatch-target-role"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "job_id"],
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
    assert claimant_id != persisted_job.source_agent_id
