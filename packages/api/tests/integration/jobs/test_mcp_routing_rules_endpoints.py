import hashlib
from typing import Any

from forkflux_api.jobs.constants import JobEventTypeEnum, JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.models import HandoffJob, JobEvent
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import (
    AgentApiTokenFactory,
    AgentIdentityFactory,
    AgentIdentityRoleFactory,
    TargetRoleFactory,
)


def _build_create_job_payload_with_routing_rules(
    *,
    target_role_key: str,
    routing_target_role_key: str,
    parent_job_id: int | None = None,
) -> dict[str, Any]:
    return {
        "parent_job_id": parent_job_id,
        "summary": "Build the feature",
        "context_payload": {"feature": "auth"},
        "target_role_key": target_role_key,
        "constraints": ["deadline:today"],
        "artifacts": [],
        "priority": JobPriorityEnum.HIGH.value,
        "routing_rules": [
            {
                "target_role_key": routing_target_role_key,
                "summary": "Review the completed work",
                "context_payload": {"review_type": "code_review"},
                "constraints": ["must approve before merge"],
                "priority": JobPriorityEnum.NORMAL.value,
                "artifacts": [],
            }
        ],
    }


async def test_create_job_with_routing_rules_returns_201_and_persists_rules(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "routing-rules-create-token"
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="routing-target-role",
        role_label="Routing Target Role",
    )
    routing_target_role = await TargetRoleFactory.create(
        db_session,
        role_key="routing-downstream-role",
        role_label="Routing Downstream Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="routing-source-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    payload = _build_create_job_payload_with_routing_rules(
        target_role_key=target_role.role_key,
        routing_target_role_key=routing_target_role.role_key,
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
    assert created_job.routing_rules is not None
    assert len(created_job.routing_rules) == 1
    assert created_job.routing_rules[0]["target_role_id"] == routing_target_role.id
    assert created_job.routing_rules[0]["target_role_key"] == routing_target_role.role_key
    assert created_job.routing_rules[0]["summary"] == "Review the completed work"


async def test_create_job_with_routing_rules_invalid_role_returns_422(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "routing-rules-invalid-role-token"
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="routing-invalid-target-role",
        role_label="Routing Invalid Target Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="routing-invalid-source-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    payload = _build_create_job_payload_with_routing_rules(
        target_role_key=target_role.role_key,
        routing_target_role_key="nonexistent-role",
    )

    response = await client.post(
        "/api/v1/mcp/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(d.get("type") == "routing_rule.invalid" for d in detail)


async def test_create_job_without_routing_rules_persists_null(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "no-routing-rules-token"
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="no-routing-target-role",
        role_label="No Routing Target Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="no-routing-source-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    payload = {
        "parent_job_id": None,
        "summary": "Simple job",
        "context_payload": {"task": "simple"},
        "target_role_key": target_role.role_key,
        "constraints": ["deadline:today"],
        "artifacts": [],
        "priority": JobPriorityEnum.NORMAL.value,
    }

    response = await client.post(
        "/api/v1/mcp/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )

    assert response.status_code == 201
    job_id = response.json()["job_id"]

    created_job = await db_session.get(HandoffJob, job_id)
    assert created_job is not None
    assert created_job.routing_rules is None


async def test_completing_job_with_routing_rules_auto_creates_downstream_jobs(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "routing-complete-token"
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="routing-complete-target",
        role_label="Routing Complete Target",
    )
    routing_target_role = await TargetRoleFactory.create(
        db_session,
        role_key="routing-complete-downstream",
        role_label="Routing Complete Downstream",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="routing-complete-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=source_agent.id,
        target_role_id=target_role.id,
    )

    # Create a job with routing rules
    payload = _build_create_job_payload_with_routing_rules(
        target_role_key=target_role.role_key,
        routing_target_role_key=routing_target_role.role_key,
    )
    response = await client.post(
        "/api/v1/mcp/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )
    assert response.status_code == 201
    job_id = response.json()["job_id"]

    # Claim the job
    response = await client.post(
        f"/api/v1/mcp/jobs/{job_id}/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 201

    # Complete the job
    response = await client.post(
        f"/api/v1/mcp/jobs/{job_id}/status",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"status": "completed"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["new_status"] == "completed"

    # Verify a downstream job was auto-created
    routed_jobs = await db_session.execute(select(HandoffJob).where(HandoffJob.parent_job_id == job_id))
    routed_job_list = list(routed_jobs.scalars())
    assert len(routed_job_list) == 1
    routed_job = routed_job_list[0]
    assert routed_job.status == JobStatusEnum.PUBLISHED
    assert routed_job.target_role_id == routing_target_role.id
    assert routed_job.source_agent_id == source_agent.id
    assert routed_job.summary == "Review the completed work"
    assert routed_job.context_payload["routed_from_job_id"] == job_id
    assert routed_job.context_payload["review_type"] == "code_review"

    # Verify a TASK_ROUTED event was created on the completing job
    routed_events = await db_session.execute(
        select(JobEvent).where(
            JobEvent.job_id == job_id,
            JobEvent.event_type == JobEventTypeEnum.TASK_ROUTED.value,
        )
    )
    routed_event_list = list(routed_events.scalars())
    assert len(routed_event_list) == 1
    assert routed_event_list[0].payload_json["routed_job_ids"] == [routed_job.id]

    # Verify a TASK_PUBLISHED event was created on the routed job
    published_events = await db_session.execute(
        select(JobEvent).where(
            JobEvent.job_id == routed_job.id,
            JobEvent.event_type == JobEventTypeEnum.TASK_PUBLISHED.value,
        )
    )
    published_event_list = list(published_events.scalars())
    assert len(published_event_list) == 1
    assert published_event_list[0].payload_json["routed_from_job_id"] == job_id

    # Verify the TASK_COMPLETED event payload contains routed_job_ids
    completed_events = await db_session.execute(
        select(JobEvent).where(
            JobEvent.job_id == job_id,
            JobEvent.event_type == JobEventTypeEnum.TASK_COMPLETED.value,
        )
    )
    completed_event_list = list(completed_events.scalars())
    assert len(completed_event_list) == 1
    assert completed_event_list[0].payload_json["routed_job_ids"] == [routed_job.id]


async def test_completing_job_without_routing_rules_creates_no_downstream(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "no-routing-complete-token"
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="no-routing-complete-target",
        role_label="No Routing Complete Target",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="no-routing-complete-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=source_agent.id,
        target_role_id=target_role.id,
    )

    # Create a job without routing rules
    payload = {
        "parent_job_id": None,
        "summary": "Simple job",
        "context_payload": {"task": "simple"},
        "target_role_key": target_role.role_key,
        "constraints": ["deadline:today"],
        "artifacts": [],
        "priority": JobPriorityEnum.NORMAL.value,
    }
    response = await client.post(
        "/api/v1/mcp/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )
    assert response.status_code == 201
    job_id = response.json()["job_id"]

    # Claim the job
    response = await client.post(
        f"/api/v1/mcp/jobs/{job_id}/claim",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 201

    # Complete the job
    response = await client.post(
        f"/api/v1/mcp/jobs/{job_id}/status",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"status": "completed"},
    )
    assert response.status_code == 200

    # Verify no downstream jobs were created
    routed_jobs = await db_session.execute(select(HandoffJob).where(HandoffJob.parent_job_id == job_id))
    routed_job_list = list(routed_jobs.scalars())
    assert len(routed_job_list) == 0

    # Verify no TASK_ROUTED event was created
    routed_events = await db_session.execute(
        select(JobEvent).where(
            JobEvent.job_id == job_id,
            JobEvent.event_type == JobEventTypeEnum.TASK_ROUTED.value,
        )
    )
    routed_event_list = list(routed_events.scalars())
    assert len(routed_event_list) == 0
