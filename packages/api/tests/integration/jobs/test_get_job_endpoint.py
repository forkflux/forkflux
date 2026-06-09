import hashlib
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.jobs.constants import JobPriorityEnum, JobStatusEnum
from src.jobs.models import HandoffJob
from tests.factories import (
    AgentApiTokenFactory,
    AgentIdentityFactory,
    HandoffJobFactory,
    JobArtifactFactory,
    TargetRoleFactory,
)


async def _create_auth_context(db_session: AsyncSession, raw_token: str) -> int:
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key=f"get-job-source-role-{raw_token}",
        role_label="Get job source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        role_id=source_role.id,
        agent_label=f"get-job-source-agent-{raw_token}",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    return source_agent.id


async def test_get_job_returns_200_and_job_with_artifacts(client: AsyncClient, db_session: AsyncSession) -> None:
    raw_token = "valid-get-job-token"
    source_agent_id = await _create_auth_context(db_session, raw_token)

    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="get-job-reviewer-role",
        role_label="Get job reviewer role",
    )
    operator_role = await TargetRoleFactory.create(
        db_session,
        role_key="get-job-operator-role",
        role_label="Get job operator role",
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        role_id=operator_role.id,
        agent_label="get-job-assignee-agent",
    )

    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    job = await HandoffJobFactory.create(
        db_session,
        parent_job_id=None,
        summary="Summarize incident timeline",
        context_payload={"ticket_id": "INC-42", "scope": "handoff"},
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.HIGH.value,
        source_agent_id=source_agent_id,
        target_role_id=reviewer_role.id,
        assignee_agent_id=assignee_agent.id,
        constraints=["deadline:today", "format:markdown"],
        failure_reason=None,
        published_at=now,
        claimed_at=None,
        started_at=None,
        completed_at=None,
        failed_at=None,
        cancelled_at=None,
        expires_at=now + timedelta(days=1),
        created_at=now,
        updated_at=now + timedelta(minutes=5),
    )

    older_artifact = await JobArtifactFactory.create(
        db_session,
        job_id=job.id,
        artifact_type="document",
        artifact_uri="s3://bucket/get-job/artifact-1.pdf",
        artifact_checksum="artifact-checksum-1",
        metadata_json={"mime_type": "application/pdf", "size": 120},
        created_at=now,
    )
    newer_artifact = await JobArtifactFactory.create(
        db_session,
        job_id=job.id,
        artifact_type="trace",
        artifact_uri="s3://bucket/get-job/artifact-2.json",
        artifact_checksum=None,
        metadata_json={"mime_type": "application/json", "size": 240},
        created_at=now + timedelta(seconds=10),
    )

    other_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=reviewer_role.id,
        created_at=now + timedelta(seconds=20),
        updated_at=now + timedelta(seconds=20),
        published_at=now + timedelta(seconds=20),
    )
    await JobArtifactFactory.create(
        db_session,
        job_id=other_job.id,
        artifact_type="binary",
        artifact_uri="s3://bucket/get-job/artifact-other.bin",
        artifact_checksum="artifact-checksum-other",
        metadata_json={"scope": "other-job"},
        created_at=now + timedelta(seconds=30),
    )

    response = await client.get(
        f"/api/v1/jobs/{job.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == job.id
    assert body["parent_job_id"] == job.parent_job_id
    assert body["summary"] == job.summary
    assert body["context_payload"] == job.context_payload
    assert body["status"] == JobStatusEnum.PUBLISHED.value
    assert body["priority"] == JobPriorityEnum.HIGH.value
    assert body["source_agent_label"].startswith("get-job-source-agent-")
    assert body["assignee_agent_label"] == assignee_agent.agent_label
    assert body["target_role_key"] == reviewer_role.role_key
    assert body["constraints"] == job.constraints
    assert body["failure_reason"] is None
    assert body["published_at"] == job.published_at.isoformat().replace("+00:00", "Z")
    assert body["claimed_at"] is None
    assert body["started_at"] is None
    assert body["completed_at"] is None
    assert body["failed_at"] is None
    assert body["cancelled_at"] is None
    assert body["expires_at"] == job.expires_at.isoformat().replace("+00:00", "Z")
    assert body["created_at"] == job.created_at.isoformat().replace("+00:00", "Z")
    assert body["updated_at"] == job.updated_at.isoformat().replace("+00:00", "Z")

    assert [artifact["type"] for artifact in body["artifacts"]] == [
        older_artifact.artifact_type,
        newer_artifact.artifact_type,
    ]
    assert body["artifacts"][0] == {
        "type": older_artifact.artifact_type,
        "uri": older_artifact.artifact_uri,
        "checksum": older_artifact.artifact_checksum,
        "metadata_json": older_artifact.metadata_json,
    }
    assert body["artifacts"][1] == {
        "type": newer_artifact.artifact_type,
        "uri": newer_artifact.artifact_uri,
        "checksum": newer_artifact.artifact_checksum,
        "metadata_json": newer_artifact.metadata_json,
    }


async def test_get_job_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.get("/api/v1/jobs/1")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_get_job_returns_401_for_invalid_bearer_token(client: AsyncClient, db_session: AsyncSession) -> None:
    valid_raw_token = "some-other-valid-get-job-token"
    source_agent_id = await _create_auth_context(db_session, valid_raw_token)

    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="get-job-auth-reviewer-role",
        role_label="Get job auth reviewer role",
    )
    await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent_id,
        target_role_id=reviewer_role.id,
    )

    response = await client.get(
        "/api/v1/jobs/1",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_get_job_returns_404_when_job_does_not_exist(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-get-job-missing-id-token"
    await _create_auth_context(db_session, raw_token)

    response = await client.get(
        "/api/v1/jobs/999999",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Handoff job not found."}
    persisted_job = await db_session.get(HandoffJob, 999_999)
    assert persisted_job is None
