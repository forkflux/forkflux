import hashlib
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.jobs.constants import JobEventTypeEnum, JobPriorityEnum, JobStatusEnum
from src.jobs.models import HandoffJob, JobArtifact, JobEvent
from tests.factories import AgentApiTokenFactory, AgentIdentityFactory, HandoffJobFactory, TargetRoleFactory


def _build_create_job_payload(*, target_role_key: str, parent_job_id: int | None) -> dict[str, Any]:
    return {
        "parent_job_id": parent_job_id,
        "summary": "Prepare incident handoff package",
        "context_payload": {"ticket_id": "TCK-900", "scope": "incident"},
        "target_role_key": target_role_key,
        "constraints": ["deadline:today"],
        "artifacts": [
            {
                "type": "document",
                "uri": "s3://bucket/job-artifacts/handoff-doc-1.pdf",
                "checksum": "checksum-doc-1",
                "metadata_json": {"mime_type": "application/pdf", "size": 100},
            },
            {
                "type": "trace",
                "uri": "s3://bucket/job-artifacts/handoff-trace-1.json",
                "checksum": None,
                "metadata_json": {"mime_type": "application/json", "size": 200},
            },
        ],
        "priority": JobPriorityEnum.HIGH.value,
    }


async def test_create_job_returns_201_and_persists_job_and_artifacts(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-create-job-token"
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="create-job-source-role",
        role_label="Create job source role",
    )
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="create-job-target-role",
        role_label="Create job target role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        role_id=source_role.id,
        agent_label="create-job-source-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    parent_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    payload = _build_create_job_payload(target_role_key=target_role.role_key, parent_job_id=parent_job.id)

    response = await client.post(
        "/v1/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"job_id"}
    job_id = body["job_id"]
    assert isinstance(job_id, int)

    created_job = await db_session.get(HandoffJob, job_id)

    assert created_job is not None
    assert created_job.parent_job_id == parent_job.id
    assert created_job.summary == payload["summary"]
    assert created_job.context_payload == payload["context_payload"]
    assert created_job.priority == JobPriorityEnum.HIGH.value
    assert created_job.status == JobStatusEnum.PUBLISHED
    assert created_job.source_agent_id == source_agent.id
    assert created_job.target_role_id == target_role.id
    assert created_job.assignee_agent_id is None
    assert created_job.constraints == payload["constraints"]
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

    artifact_rows = await db_session.execute(
        select(JobArtifact).where(JobArtifact.job_id == job_id).order_by(JobArtifact.id.asc())
    )
    created_artifacts = list(artifact_rows.scalars())

    assert len(created_artifacts) == 2
    assert created_artifacts[0].artifact_type == payload["artifacts"][0]["type"]
    assert created_artifacts[0].artifact_uri == payload["artifacts"][0]["uri"]
    assert created_artifacts[0].artifact_checksum == payload["artifacts"][0]["checksum"]
    assert created_artifacts[0].metadata_json == payload["artifacts"][0]["metadata_json"]
    assert created_artifacts[1].artifact_type == payload["artifacts"][1]["type"]
    assert created_artifacts[1].artifact_uri == payload["artifacts"][1]["uri"]
    assert created_artifacts[1].artifact_checksum == payload["artifacts"][1]["checksum"]
    assert created_artifacts[1].metadata_json == payload["artifacts"][1]["metadata_json"]

    event_rows = await db_session.execute(select(JobEvent).where(JobEvent.job_id == job_id).order_by(JobEvent.id.asc()))
    created_events = list(event_rows.scalars())

    assert len(created_events) == 1
    assert created_events[0].event_type == JobEventTypeEnum.TASK_PUBLISHED.value
    assert created_events[0].previous_status is None
    assert created_events[0].current_status == JobStatusEnum.PUBLISHED
    assert created_events[0].actor_agent_id == source_agent.id
    assert created_events[0].payload_json == {
        "priority": payload["priority"],
        "target_role_id": target_role.id,
        "artifact_count": len(payload["artifacts"]),
    }


async def test_create_job_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    payload = _build_create_job_payload(target_role_key="role-missing-auth", parent_job_id=None)

    response = await client.post("/v1/jobs", json=payload)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_create_job_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    valid_raw_token = "some-other-valid-create-job-token"
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="create-job-auth-source-role",
        role_label="Create job auth source role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=source_role.id,
        agent_label="create-job-auth-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(valid_raw_token.encode()).hexdigest(),
        agent_id=identity.id,
        is_active=True,
    )
    payload = _build_create_job_payload(target_role_key="any-target-role", parent_job_id=None)

    response = await client.post(
        "/v1/jobs",
        headers={"Authorization": "Bearer invalid-token"},
        json=payload,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_create_job_returns_422_when_parent_job_id_is_invalid(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-create-job-parent-validation-token"
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="create-job-parent-validation-source-role",
        role_label="Create job parent validation source role",
    )
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="create-job-parent-validation-target-role",
        role_label="Create job parent validation target role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        role_id=source_role.id,
        agent_label="create-job-parent-validation-source-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    payload = _build_create_job_payload(target_role_key=target_role.role_key, parent_job_id=999_999)

    response = await client.post(
        "/v1/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "parent_job_id"],
                "msg": "Parent job is invalid.",
                "type": "parent_job.invalid",
                "input": 999_999,
                "ctx": {},
            }
        ]
    }


async def test_create_job_returns_422_when_target_role_key_is_invalid(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-create-job-target-role-validation-token"
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="create-job-target-validation-source-role",
        role_label="Create job target validation source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        role_id=source_role.id,
        agent_label="create-job-target-validation-source-agent",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    payload = _build_create_job_payload(target_role_key="missing-role-key", parent_job_id=None)

    response = await client.post(
        "/v1/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["body", "target_role_key"],
                "msg": "Target role is invalid.",
                "type": "target_role.invalid",
                "input": "missing-role-key",
                "ctx": {},
            }
        ]
    }
