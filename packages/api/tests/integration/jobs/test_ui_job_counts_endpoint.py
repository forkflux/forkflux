from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentIdentityFactory, HandoffJobFactory, TargetRoleFactory


async def test_ui_job_counts_returns_200_with_zeroed_counts_for_empty_database(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/jobs/counts")

    assert response.status_code == 200
    payload = response.json()
    counts = payload["counts"]
    assert counts["published"] == 0
    assert counts["claimed"] == 0
    assert counts["in_progress"] == 0
    assert counts["blocked"] == 0
    assert counts["completed"] == 0
    assert counts["failed"] == 0
    assert counts["cancelled"] == 0


async def test_ui_job_counts_returns_200_with_correct_counts_for_mixed_statuses(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="ui-counts-role",
        role_label="UI Counts Role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="ui-counts-source",
    )

    await HandoffJobFactory.create(
        db_session,
        status="published",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        status="published",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        status="in_progress",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        status="completed",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        status="completed",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        status="failed",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )
    await HandoffJobFactory.create(
        db_session,
        status="cancelled",
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    response = await client.get("/api/v1/ui/jobs/counts")

    assert response.status_code == 200
    payload = response.json()
    counts = payload["counts"]
    assert counts["published"] == 2
    assert counts["claimed"] == 0
    assert counts["in_progress"] == 1
    assert counts["blocked"] == 0
    assert counts["completed"] == 2
    assert counts["failed"] == 1
    assert counts["cancelled"] == 1
