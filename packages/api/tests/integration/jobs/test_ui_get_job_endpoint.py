from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import (
    AgentIdentityFactory,
    HandoffJobFactory,
    JobArtifactFactory,
    JobEventFactory,
    TargetRoleFactory,
)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def test_ui_get_job_returns_200_with_job_artifacts_and_events(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-get-detail-role",
        role_label="UI Get Detail Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-get-detail-source",
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-get-detail-assignee",
    )
    job = await HandoffJobFactory.create(
        db_session,
        summary="UI detail job",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=assignee_agent.id,
    )

    artifact = await JobArtifactFactory.create(
        db_session,
        job_id=job.id,
        artifact_type="document",
        artifact_uri="s3://bucket/ui-get-detail-doc.pdf",
        artifact_checksum="ui-get-detail-checksum",
        metadata_json={"mime_type": "application/pdf"},
    )

    event = await JobEventFactory.create(
        db_session,
        job_id=job.id,
        actor_agent_id=source_agent.id,
    )

    response = await client.get(f"/api/v1/ui/jobs/{job.id}")

    assert response.status_code == 200
    payload = response.json()

    assert payload["id"] == job.id
    assert payload["parent_job_id"] is None
    assert payload["parent_job_summary"] is None
    assert payload["summary"] == "UI detail job"
    assert payload["status"] == "published"
    assert payload["priority"] == 20
    assert payload["source_agent_label"] == source_agent.agent_label
    assert payload["assignee_agent_label"] == assignee_agent.agent_label
    assert payload["target_role_label"] == target_role.role_label
    assert payload["failure_reason"] is None
    assert payload["blocked_reason"] is None
    assert payload["published_at"] is not None
    assert payload["created_at"] is not None
    assert payload["updated_at"] is not None

    assert len(payload["artifacts"]) == 1
    artifact_item = payload["artifacts"][0]
    assert artifact_item["id"] == artifact.id
    assert artifact_item["artifact_type"] == "document"
    assert artifact_item["artifact_uri"] == "s3://bucket/ui-get-detail-doc.pdf"
    assert artifact_item["artifact_checksum"] == "ui-get-detail-checksum"
    assert artifact_item["metadata_json"] == {"mime_type": "application/pdf"}
    assert artifact_item["created_at"] is not None

    assert len(payload["events"]) == 1
    event_item = payload["events"][0]
    assert event_item["event_type"] == event.event_type
    assert event_item["previous_status"] == event.previous_status.value
    assert event_item["current_status"] == event.current_status.value
    assert event_item["actor_agent_label"] == source_agent.agent_label
    assert event_item["payload_json"] == event.payload_json
    assert event_item["created_at"] is not None


async def test_ui_get_job_returns_404_for_missing_job(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/jobs/999_999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Handoff job not found."


async def test_ui_get_job_returns_events_ordered_by_created_at_desc(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-get-order-role",
        role_label="UI Get Order Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-get-order-source",
    )
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    created_at_base = datetime.now(timezone.utc)
    first_event = await JobEventFactory.create(
        db_session,
        job_id=job.id,
        actor_agent_id=source_agent.id,
        created_at=created_at_base,
    )
    second_event = await JobEventFactory.create(
        db_session,
        job_id=job.id,
        actor_agent_id=source_agent.id,
        created_at=created_at_base + timedelta(seconds=10),
    )
    third_event = await JobEventFactory.create(
        db_session,
        job_id=job.id,
        actor_agent_id=source_agent.id,
        created_at=created_at_base + timedelta(seconds=20),
    )

    response = await client.get(f"/api/v1/ui/jobs/{job.id}")

    assert response.status_code == 200
    payload = response.json()

    assert len(payload["events"]) == 3
    event_created_ats = [_parse_iso(event["created_at"]) for event in payload["events"]]
    assert event_created_ats[0] == third_event.created_at
    assert event_created_ats[1] == second_event.created_at
    assert event_created_ats[2] == first_event.created_at


async def test_ui_get_job_returns_parent_job_summary(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-get-parent-role",
        role_label="UI Get Parent Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-get-parent-source",
    )
    parent_job = await HandoffJobFactory.create(
        db_session,
        summary="Parent job for UI detail",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    child_job = await HandoffJobFactory.create(
        db_session,
        parent_job_id=parent_job.id,
        summary="Child job for UI detail",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    response = await client.get(f"/api/v1/ui/jobs/{child_job.id}")

    assert response.status_code == 200
    payload = response.json()

    assert payload["id"] == child_job.id
    assert payload["parent_job_id"] == parent_job.id
    assert payload["parent_job_summary"] == "Parent job for UI detail"


async def test_ui_get_job_returns_empty_artifacts_and_events_when_none_exist(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-get-empty-role",
        role_label="UI Get Empty Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-get-empty-source",
    )
    job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    response = await client.get(f"/api/v1/ui/jobs/{job.id}")

    assert response.status_code == 200
    payload = response.json()

    assert payload["artifacts"] == []
    assert payload["events"] == []
