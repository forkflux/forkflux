import hashlib
from datetime import datetime, timezone
from typing import Any

from forkflux_api.jobs.constants import DependencyTypeEnum, JobEventTypeEnum, JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.models import HandoffJob, JobArtifact, JobDependency, JobEvent
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import (
    AgentApiTokenFactory,
    AgentIdentityFactory,
    AgentIdentityRoleFactory,
    HandoffJobFactory,
    JobDependencyFactory,
    TargetRoleFactory,
)


def _build_create_job_payload_with_blocked_by(*, target_role_key: str, blocked_by: list[int]) -> dict[str, Any]:
    return {
        "parent_job_id": None,
        "summary": "Job with dependencies",
        "context_payload": {"task": "fan-in job"},
        "target_role_key": target_role_key,
        "constraints": ["deadline:today"],
        "artifacts": [],
        "priority": JobPriorityEnum.NORMAL.value,
        "blocked_by": blocked_by,
    }


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


async def test_create_job_with_blocked_by_creates_pending_job_and_dependency_edges(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "blocked-by-create-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="blocked-by-target-role",
        role_label="Blocked by target role",
        agent_label="blocked-by-source-agent",
    )

    upstream_job_1 = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
    )
    upstream_job_2 = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
    )

    payload = _build_create_job_payload_with_blocked_by(
        target_role_key="blocked-by-target-role",
        blocked_by=[upstream_job_1.id, upstream_job_2.id],
    )

    response = await client.post(
        "/api/v1/mcp/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )

    assert response.status_code == 201
    job_id = response.json()["job_id"]

    created_job = await db_session.get(HandoffJob, job_id)
    assert created_job is not None
    assert created_job.status == JobStatusEnum.PENDING
    assert created_job.retry_count == 0
    assert created_job.max_retries == 3

    dep_rows = await db_session.execute(
        select(JobDependency).where(JobDependency.downstream_job_id == job_id).order_by(JobDependency.id.asc())
    )
    deps = list(dep_rows.scalars())
    assert len(deps) == 2
    assert all(d.dep_type == DependencyTypeEnum.BLOCKS for d in deps)
    upstream_ids = {d.upstream_job_id for d in deps}
    assert upstream_ids == {upstream_job_1.id, upstream_job_2.id}

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.id.asc()))
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_PENDING.value
    assert events[0].current_status == JobStatusEnum.PENDING


async def test_create_job_with_blocked_by_returns_422_when_upstream_job_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "blocked-by-validation-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="blocked-by-validation-role",
        role_label="Blocked by validation role",
        agent_label="blocked-by-validation-agent",
    )

    payload = _build_create_job_payload_with_blocked_by(
        target_role_key="blocked-by-validation-role",
        blocked_by=[999_999],
    )

    response = await client.post(
        "/api/v1/mcp/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "blocked_by_job.invalid"


async def test_create_job_with_blocked_by_all_completed_transitions_to_published(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "blocked-by-completed-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="blocked-by-completed-role",
        role_label="Blocked by completed role",
        agent_label="blocked-by-completed-agent",
    )

    upstream_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
    )

    payload = _build_create_job_payload_with_blocked_by(
        target_role_key="blocked-by-completed-role",
        blocked_by=[upstream_job.id],
    )

    response = await client.post(
        "/api/v1/mcp/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )

    assert response.status_code == 201
    job_id = response.json()["job_id"]

    created_job = await db_session.get(HandoffJob, job_id)
    assert created_job is not None
    assert created_job.status == JobStatusEnum.PUBLISHED


async def test_barrier_sync_activates_downstream_job_when_upstream_completes(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "barrier-sync-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="barrier-sync-role",
        role_label="Barrier sync role",
        agent_label="barrier-sync-agent",
    )

    upstream_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    downstream_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.PENDING,
    )

    await JobDependencyFactory.create(
        db_session,
        upstream_job_id=upstream_job.id,
        downstream_job_id=downstream_job.id,
        dep_type=DependencyTypeEnum.BLOCKS,
        created_at=downstream_job.created_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{upstream_job.id}/status",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"status": JobStatusEnum.COMPLETED.value},
    )

    assert response.status_code == 200

    await db_session.refresh(downstream_job)
    assert downstream_job.status == JobStatusEnum.PUBLISHED

    event_rows = await db_session.execute(
        select(JobEvent).where(JobEvent.job_id == downstream_job.id).order_by(JobEvent.id.asc())
    )
    events = list(event_rows.scalars())
    assert any(e.event_type == JobEventTypeEnum.TASK_ACTIVATED.value for e in events)


async def test_pending_job_cannot_be_claimed(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "pending-claim-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="pending-claim-role",
        role_label="Pending claim role",
        agent_label="pending-claim-agent",
    )

    pending_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.PENDING,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{pending_job.id}/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422


async def test_reject_job_creates_reopen_iteration(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "reject-job-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-job-role",
        role_label="Reject job role",
        agent_label="reject-job-agent",
    )

    # The original work job — must be COMPLETED.
    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
        retry_count=0,
        max_retries=3,
    )

    # The reviewing job — must be IN_PROGRESS and assigned to the caller.
    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    # Create a BLOCKS edge from original_job to reviewing_job — the reviewer
    # was waiting on the original work to complete.
    await JobDependencyFactory.create(
        db_session,
        upstream_job_id=original_job.id,
        downstream_job_id=reviewing_job.id,
        dep_type=DependencyTypeEnum.BLOCKS,
        created_at=reviewing_job.created_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": original_job.id,
            "reason": "Tests failed on edge case",
        },
    )

    assert response.status_code == 201
    body = response.json()
    new_job_id = body["job_id"]
    assert body["original_job_id"] == original_job.id
    assert body["retry_count"] == 1

    new_job = await db_session.get(HandoffJob, new_job_id)
    assert new_job is not None
    assert new_job.status == JobStatusEnum.PUBLISHED
    assert new_job.retry_count == 1
    assert new_job.max_retries == 3
    # parent_job_id is inherited from the original job's parent, not the target.
    assert new_job.parent_job_id == original_job.parent_job_id
    assert new_job.target_role_id == target_role_id

    # REOPEN_OF edge from original to retry.
    dep_rows = await db_session.execute(select(JobDependency).where(JobDependency.downstream_job_id == new_job_id))
    deps = list(dep_rows.scalars())
    assert len(deps) == 1
    assert deps[0].dep_type == DependencyTypeEnum.REOPEN_OF
    assert deps[0].upstream_job_id == original_job.id

    # New BLOCKS edge from retry to reviewer.
    reviewer_dep_rows = await db_session.execute(
        select(JobDependency).where(JobDependency.downstream_job_id == reviewing_job.id)
    )
    reviewer_deps = list(reviewer_dep_rows.scalars())
    assert len(reviewer_deps) == 1
    assert reviewer_deps[0].dep_type == DependencyTypeEnum.BLOCKS
    assert reviewer_deps[0].upstream_job_id == new_job_id

    # Old BLOCKS edge from original to reviewer is deleted.
    old_edge_rows = await db_session.execute(
        select(JobDependency).where(
            JobDependency.upstream_job_id == original_job.id,
            JobDependency.downstream_job_id == reviewing_job.id,
            JobDependency.dep_type == DependencyTypeEnum.BLOCKS,
        )
    )
    assert list(old_edge_rows.scalars()) == []

    # Reviewer transitioned to PENDING.
    await db_session.refresh(reviewing_job)
    assert reviewing_job.status == JobStatusEnum.PENDING

    # Reviewer has a TASK_PENDING event.
    reviewer_event_rows = await db_session.execute(
        select(JobEvent).where(JobEvent.job_id == reviewing_job.id).order_by(JobEvent.id.desc()).limit(1)
    )
    reviewer_events = list(reviewer_event_rows.scalars())
    assert len(reviewer_events) == 1
    assert reviewer_events[0].event_type == JobEventTypeEnum.TASK_PENDING.value
    assert reviewer_events[0].current_status == JobStatusEnum.PENDING

    # Retry job has a TASK_PUBLISHED event.
    event_rows = await db_session.execute(
        select(JobEvent).where(JobEvent.job_id == new_job_id).order_by(JobEvent.id.asc())
    )
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_PUBLISHED.value
    assert events[0].payload_json["retry_count"] == 1
    assert events[0].payload_json["rejection_reason"] == "Tests failed on edge case"


async def test_reject_job_returns_422_when_reviewing_job_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "reject-not-found-token"
    await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-not-found-role",
        role_label="Reject not found role",
        agent_label="reject-not-found-agent",
    )

    response = await client.post(
        "/api/v1/mcp/jobs/999_999/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": 999_998,
            "reason": "not found",
        },
    )

    assert response.status_code == 422
    # The reviewing job (path job_id) is the missing entity; the error must be
    # attributed to job_id in the path, not to target_job_id in the body.
    detail = response.json()["detail"][0]
    assert detail["loc"] == ["path", "job_id"]
    assert detail["input"] == 999_999


async def test_reject_job_returns_422_when_target_job_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """A missing target job (body target_job_id) must be attributed to
    target_job_id in the body, distinct from a missing reviewing job."""
    raw_token = "reject-target-not-found-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-target-not-found-role",
        role_label="Reject target not found role",
        agent_label="reject-target-not-found-agent",
    )

    # Reviewing job exists, is IN_PROGRESS, and is assigned to the caller so
    # the service reaches the target_job lookup, which then misses.
    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": 999_998,
            "reason": "target missing",
        },
    )

    assert response.status_code == 422
    detail = response.json()["detail"][0]
    assert detail["loc"] == ["body", "target_job_id"]
    assert detail["input"] == 999_998


async def test_reject_job_returns_422_when_caller_not_assignee(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "reject-unauthorized-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-unauthorized-role",
        role_label="Reject unauthorized role",
        agent_label="reject-unauthorized-agent",
    )

    other_agent_id, _ = await _create_authenticated_agent(
        db_session,
        raw_token="reject-other-token",
        role_key="reject-other-role",
        role_label="Reject other role",
        agent_label="reject-other-agent",
    )

    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
    )

    # Reviewing job assigned to a different agent.
    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=other_agent_id,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": original_job.id,
            "reason": "unauthorized rejection",
        },
    )

    assert response.status_code == 422


async def test_reject_job_returns_422_when_target_not_completed(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "reject-target-not-completed-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-target-not-completed-role",
        role_label="Reject target not completed role",
        agent_label="reject-target-not-completed-agent",
    )

    # Target job is still IN_PROGRESS, not COMPLETED.
    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
    )

    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": original_job.id,
            "reason": "target not done",
        },
    )

    assert response.status_code == 422


async def test_reject_job_returns_422_when_max_retries_exceeded(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "reject-max-retries-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-max-retries-role",
        role_label="Reject max retries role",
        agent_label="reject-max-retries-agent",
    )

    # Original job has exhausted its retry budget.
    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
        retry_count=3,
        max_retries=3,
    )

    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    # Create BLOCKS edge so the reject reaches the max_retries check.
    await JobDependencyFactory.create(
        db_session,
        upstream_job_id=original_job.id,
        downstream_job_id=reviewing_job.id,
        dep_type=DependencyTypeEnum.BLOCKS,
        created_at=reviewing_job.created_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": original_job.id,
            "reason": "try again",
        },
    )

    assert response.status_code == 422


async def test_reject_job_returns_422_when_no_blocks_edge(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "reject-no-edge-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-no-edge-role",
        role_label="Reject no edge role",
        agent_label="reject-no-edge-agent",
    )

    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
    )

    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    # No BLOCKS edge created — reject should fail.

    response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": original_job.id,
            "reason": "no edge",
        },
    )

    assert response.status_code == 422


async def test_reject_job_returns_422_when_reason_is_whitespace_only(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Whitespace-only rejection reasons must be rejected at the schema layer."""
    raw_token = "reject-whitespace-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-whitespace-role",
        role_label="Reject whitespace role",
        agent_label="reject-whitespace-agent",
    )

    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
    )

    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    await JobDependencyFactory.create(
        db_session,
        upstream_job_id=original_job.id,
        downstream_job_id=reviewing_job.id,
        dep_type=DependencyTypeEnum.BLOCKS,
        created_at=reviewing_job.created_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": original_job.id,
            "reason": "   ",
        },
    )

    assert response.status_code == 422


async def test_get_pending_job_returns_200_with_null_published_at(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "get-pending-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="get-pending-role",
        role_label="Get pending role",
        agent_label="get-pending-agent",
    )

    pending_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.PENDING,
        published_at=None,
    )

    response = await client.get(
        f"/api/v1/mcp/jobs/{pending_job.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == JobStatusEnum.PENDING.value
    assert body["published_at"] is None
    assert body["retry_count"] == 0
    assert body["max_retries"] == 3


async def test_full_reject_retry_barrier_claim_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Full lifecycle: reject → retry created → reviewer PENDING → retry completes → reviewer PUBLISHED → claimable."""
    raw_token = "lifecycle-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="lifecycle-role",
        role_label="Lifecycle role",
        agent_label="lifecycle-agent",
    )

    # Assign the target role to the agent so it can claim jobs.
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=source_agent_id,
        target_role_id=target_role_id,
    )

    # Original work job — COMPLETED.
    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
        retry_count=0,
        max_retries=3,
    )

    # Reviewing job — IN_PROGRESS, assigned to caller.
    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
        claimed_at=datetime.now(timezone.utc),
        started_at=datetime.now(timezone.utc),
    )

    # BLOCKS edge: original → reviewer.
    await JobDependencyFactory.create(
        db_session,
        upstream_job_id=original_job.id,
        downstream_job_id=reviewing_job.id,
        dep_type=DependencyTypeEnum.BLOCKS,
        created_at=reviewing_job.created_at,
    )

    # Step 1: Reject — creates retry, reviewer goes to PENDING.
    reject_response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"target_job_id": original_job.id, "reason": "Needs fixes"},
    )
    assert reject_response.status_code == 201
    retry_job_id = reject_response.json()["job_id"]

    # Verify reviewer is PENDING with cleared ownership.
    await db_session.refresh(reviewing_job)
    assert reviewing_job.status == JobStatusEnum.PENDING
    assert reviewing_job.assignee_agent_id is None
    assert reviewing_job.claimed_at is None
    assert reviewing_job.started_at is None

    # Step 2: Claim and complete the retry job.
    retry_job = await db_session.get(HandoffJob, retry_job_id)
    assert retry_job is not None
    assert retry_job.status == JobStatusEnum.PUBLISHED

    # Assign the retry to an agent and transition to IN_PROGRESS.
    retry_job.status = JobStatusEnum.IN_PROGRESS
    retry_job.assignee_agent_id = source_agent_id
    retry_job.claimed_at = datetime.now(timezone.utc)
    retry_job.started_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Complete the retry — barrier sync should transition reviewer to PUBLISHED.
    complete_response = await client.post(
        f"/api/v1/mcp/jobs/{retry_job_id}/status",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"status": JobStatusEnum.COMPLETED.value},
    )
    assert complete_response.status_code == 200

    # Step 3: Verify reviewer is now PUBLISHED and claimable.
    await db_session.refresh(reviewing_job)
    assert reviewing_job.status == JobStatusEnum.PUBLISHED
    assert reviewing_job.assignee_agent_id is None

    # Step 4: Claim the reviewer — should succeed.
    claim_response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert claim_response.status_code == 201
    claim_body = claim_response.json()
    assert claim_body["status"] == JobStatusEnum.IN_PROGRESS.value
    assert claim_body["assignee_agent_label"] is not None


async def test_reject_job_creates_rejection_reason_artifact(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """reject_job must create a rejection_reason artifact on the new job."""
    raw_token = "reject-artifact-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reject-artifact-role",
        role_label="Reject artifact role",
        agent_label="reject-artifact-agent",
    )

    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
        retry_count=0,
        max_retries=3,
    )

    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    await JobDependencyFactory.create(
        db_session,
        upstream_job_id=original_job.id,
        downstream_job_id=reviewing_job.id,
        dep_type=DependencyTypeEnum.BLOCKS,
        created_at=reviewing_job.created_at,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": original_job.id,
            "reason": "Tests failed on edge case",
        },
    )

    assert response.status_code == 201
    new_job_id = response.json()["job_id"]

    artifact_rows = await db_session.execute(
        select(JobArtifact).where(
            JobArtifact.job_id == new_job_id,
            JobArtifact.artifact_type == "rejection_reason",
        )
    )
    artifacts = list(artifact_rows.scalars())
    assert len(artifacts) == 1
    assert artifacts[0].artifact_uri == "inline://rejection_reason"
    assert artifacts[0].artifact_checksum is None
    assert artifacts[0].metadata_json["reason"] == "Tests failed on edge case"
    assert artifacts[0].metadata_json["original_job_id"] == original_job.id
    assert artifacts[0].metadata_json["rejected_by_job_id"] == reviewing_job.id
    assert artifacts[0].metadata_json["retry_count"] == 1


async def test_get_reopen_context_returns_focused_data_after_reject(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /jobs/{id}/reopen-context must return focused diff data, not full context_payload."""
    raw_token = "reopen-context-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reopen-context-role",
        role_label="Reopen context role",
        agent_label="reopen-context-agent",
    )

    original_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.COMPLETED,
        retry_count=0,
        max_retries=3,
        summary="Fix the login bug",
        context_payload={"task": "fix login", "details": "very long context" * 100},
        constraints=["deadline:today", "no-breaking-changes"],
    )

    reviewing_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.IN_PROGRESS,
        assignee_agent_id=source_agent_id,
    )

    await JobDependencyFactory.create(
        db_session,
        upstream_job_id=original_job.id,
        downstream_job_id=reviewing_job.id,
        dep_type=DependencyTypeEnum.BLOCKS,
        created_at=reviewing_job.created_at,
    )

    reject_response = await client.post(
        f"/api/v1/mcp/jobs/{reviewing_job.id}/reject",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={
            "target_job_id": original_job.id,
            "reason": "Tests failed on edge case",
        },
    )
    assert reject_response.status_code == 201
    new_job_id = reject_response.json()["job_id"]

    response = await client.get(
        f"/api/v1/mcp/jobs/{new_job_id}/reopen-context",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == new_job_id
    assert body["original_job_id"] == original_job.id
    assert body["rejected_by_job_id"] == reviewing_job.id
    assert body["retry_count"] == 1
    assert body["max_retries"] == 3
    assert body["rejection_reason"] == "Tests failed on edge case"
    assert "[Retry 1]" in body["summary"]
    assert body["constraints"] == ["deadline:today", "no-breaking-changes"]
    assert body["target_role_key"] == "reopen-context-role"
    # The full context_payload must NOT be in the response.
    assert "context_payload" not in body


async def test_get_reopen_context_returns_422_for_non_reopen_job(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /jobs/{id}/reopen-context must return 422 for a regular (non-reopen) job."""
    raw_token = "reopen-422-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="reopen-422-role",
        role_label="Reopen 422 role",
        agent_label="reopen-422-agent",
    )

    regular_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.PUBLISHED,
        context_payload={"task": "regular job"},
    )

    response = await client.get(
        f"/api/v1/mcp/jobs/{regular_job.id}/reopen-context",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422


async def test_change_job_status_failed_to_in_progress_blocked_when_max_retries_exceeded(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """FAILED → IN_PROGRESS must return 422 when retry_count >= max_retries."""
    raw_token = "max-retries-status-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="max-retries-status-role",
        role_label="Max retries status role",
        agent_label="max-retries-status-agent",
    )

    failed_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.FAILED,
        assignee_agent_id=source_agent_id,
        retry_count=3,
        max_retries=3,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{failed_job.id}/status",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"status": JobStatusEnum.IN_PROGRESS.value},
    )

    assert response.status_code == 422

    # Job must remain FAILED with retry_count unchanged.
    await db_session.refresh(failed_job)
    assert failed_job.status == JobStatusEnum.FAILED
    assert failed_job.retry_count == 3


async def test_change_job_status_failed_to_in_progress_increments_retry_count(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """FAILED → IN_PROGRESS must increment retry_count and succeed when under max_retries."""
    raw_token = "retry-increment-token"
    source_agent_id, target_role_id = await _create_authenticated_agent(
        db_session,
        raw_token=raw_token,
        role_key="retry-increment-role",
        role_label="Retry increment role",
        agent_label="retry-increment-agent",
    )

    failed_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=target_role_id,
        status=JobStatusEnum.FAILED,
        assignee_agent_id=source_agent_id,
        retry_count=1,
        max_retries=3,
    )

    response = await client.post(
        f"/api/v1/mcp/jobs/{failed_job.id}/status",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"status": JobStatusEnum.IN_PROGRESS.value},
    )

    assert response.status_code == 200

    await db_session.refresh(failed_job)
    assert failed_job.status == JobStatusEnum.IN_PROGRESS
    assert failed_job.retry_count == 2

    # The event payload must include the new retry_count.
    event_rows = await db_session.execute(
        select(JobEvent).where(JobEvent.job_id == failed_job.id).order_by(JobEvent.id.desc()).limit(1)
    )
    events = list(event_rows.scalars())
    assert len(events) == 1
    assert events[0].event_type == JobEventTypeEnum.TASK_RESTARTED.value
    assert events[0].payload_json["retry_count"] == 2
