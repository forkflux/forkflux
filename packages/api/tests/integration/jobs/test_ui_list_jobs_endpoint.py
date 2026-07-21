from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentIdentityFactory, HandoffJobFactory, TargetRoleFactory


async def test_ui_list_jobs_returns_200_with_default_params(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-list-default-role",
        role_label="UI List Default Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-default-source",
    )
    job = await HandoffJobFactory.create(
        db_session,
        summary="Default params job",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    response = await client.get("/api/v1/ui/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert len(payload["items"]) == 1

    item = payload["items"][0]
    assert item["id"] == job.id
    assert item["parent_job_id"] is None
    assert item["parent_job_summary"] is None
    assert item["summary"] == "Default params job"
    assert item["status"] == "published"
    assert item["priority"] == 20
    assert item["source_agent_label"] == source_agent.agent_label
    assert item["assignee_agent_label"] is None
    assert item["target_role_label"] == target_role.role_label
    assert item["created_at"] is not None


async def test_ui_list_jobs_returns_200_with_empty_list_when_no_jobs(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["limit"] == 50
    assert payload["offset"] == 0
    assert payload["items"] == []


async def test_ui_list_jobs_returns_parent_job_summary(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-list-parent-role",
        role_label="UI List Parent Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-parent-source",
    )
    parent_job = await HandoffJobFactory.create(
        db_session,
        summary="Parent job for UI",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    child_job = await HandoffJobFactory.create(
        db_session,
        parent_job_id=parent_job.id,
        summary="Child job for UI",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    response = await client.get("/api/v1/ui/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2

    by_id = {item["id"]: item for item in payload["items"]}

    parent_item = by_id[parent_job.id]
    assert parent_item["parent_job_id"] is None
    assert parent_item["parent_job_summary"] is None

    child_item = by_id[child_job.id]
    assert child_item["parent_job_id"] == parent_job.id
    assert child_item["parent_job_summary"] == "Parent job for UI"


async def test_ui_list_jobs_filters_by_status(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-list-filter-status-role",
        role_label="UI List Filter Status Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-filter-status-source",
    )
    published_job = await HandoffJobFactory.create(
        db_session,
        summary="Published job",
        status="published",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Completed job",
        status="completed",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    response = await client.get("/api/v1/ui/jobs", params={"status": "published"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["id"] == published_job.id


async def test_ui_list_jobs_filters_by_multiple_statuses(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-list-multi-status-role",
        role_label="UI List Multi Status Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-multi-status-source",
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Published job",
        status="published",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Completed job",
        status="completed",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Failed job",
        status="failed",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    response = await client.get(
        "/api/v1/ui/jobs",
        params=[("status", "published"), ("status", "completed")],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    statuses = {item["status"] for item in payload["items"]}
    assert statuses == {"published", "completed"}


async def test_ui_list_jobs_applies_limit(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-list-limit-role",
        role_label="UI List Limit Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-limit-source",
    )
    for _ in range(5):
        await HandoffJobFactory.create(
            db_session,
            source_agent_id=source_agent.id,
            target_role_id=target_role.id,
        )

    response = await client.get("/api/v1/ui/jobs", params={"limit": 2})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert payload["limit"] == 2
    assert payload["offset"] == 0
    assert len(payload["items"]) == 2


async def test_ui_list_jobs_applies_offset_for_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-list-offset-role",
        role_label="UI List Offset Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-offset-source",
    )
    from datetime import datetime, timedelta, timezone

    base_dt = datetime(2026, 4, 1, tzinfo=timezone.utc)
    created_job_ids = []
    for day_offset in range(5):
        current_dt = base_dt + timedelta(days=day_offset)
        job = await HandoffJobFactory.create(
            db_session,
            summary=f"Job day {day_offset}",
            source_agent_id=source_agent.id,
            target_role_id=target_role.id,
            created_at=current_dt,
            updated_at=current_dt,
            published_at=current_dt,
        )
        created_job_ids.append(job.id)

    first_page = await client.get("/api/v1/ui/jobs", params={"limit": 2, "offset": 0})
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert first_payload["total"] == 5
    assert first_payload["limit"] == 2
    assert first_payload["offset"] == 0
    assert [item["id"] for item in first_payload["items"]] == created_job_ids[0:2]

    second_page = await client.get("/api/v1/ui/jobs", params={"limit": 2, "offset": 2})
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert second_payload["total"] == 5
    assert second_payload["limit"] == 2
    assert second_payload["offset"] == 2
    assert [item["id"] for item in second_payload["items"]] == created_job_ids[2:4]

    third_page = await client.get("/api/v1/ui/jobs", params={"limit": 2, "offset": 4})
    assert third_page.status_code == 200
    third_payload = third_page.json()
    assert third_payload["total"] == 5
    assert third_payload["limit"] == 2
    assert third_payload["offset"] == 4
    assert [item["id"] for item in third_payload["items"]] == created_job_ids[4:5]


async def test_ui_list_jobs_orders_by_created_at_desc(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-list-order-desc-role",
        role_label="UI List Order Desc Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-order-desc-source",
    )
    from datetime import datetime, timedelta, timezone

    base_dt = datetime(2026, 5, 1, tzinfo=timezone.utc)
    created_job_ids = []
    for day_offset in range(3):
        current_dt = base_dt + timedelta(days=day_offset)
        job = await HandoffJobFactory.create(
            db_session,
            summary=f"Order job {day_offset}",
            source_agent_id=source_agent.id,
            target_role_id=target_role.id,
            created_at=current_dt,
            updated_at=current_dt,
            published_at=current_dt,
        )
        created_job_ids.append(job.id)

    response = await client.get("/api/v1/ui/jobs", params={"order": "created_at_desc"})

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == list(reversed(created_job_ids))


async def test_ui_list_jobs_returns_assignee_label_when_assigned(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-list-assignee-role",
        role_label="UI List Assignee Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-assignee-source",
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-list-assignee-agent",
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Assigned job",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
        assignee_agent_id=assignee_agent.id,
    )

    response = await client.get("/api/v1/ui/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["assignee_agent_label"] == assignee_agent.agent_label
    assert payload["items"][0]["source_agent_label"] == source_agent.agent_label


async def test_ui_list_jobs_rejects_invalid_status_with_422(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/jobs", params={"status": "invalid_status"})

    assert response.status_code == 422


async def test_ui_list_jobs_rejects_limit_below_minimum_with_422(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/jobs", params={"limit": 0})

    assert response.status_code == 422


async def test_ui_list_jobs_rejects_offset_below_zero_with_422(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/jobs", params={"offset": -1})

    assert response.status_code == 422
