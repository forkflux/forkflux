from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentIdentityFactory, AgentIdentityRoleFactory, TargetRoleFactory


async def test_list_all_agents_returns_200_and_all_db_fields_without_auth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    agent_backend = await AgentIdentityFactory.create(
        db_session,
        agent_label="backend-agent",
        tool_family="backend",
    )
    agent_frontend = await AgentIdentityFactory.create(
        db_session,
        agent_label="frontend-agent",
        tool_family=None,
    )

    response = await client.get("/api/v1/ui/agents")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2

    by_label = {item["agent_label"]: item for item in payload}

    backend_item = by_label[agent_backend.agent_label]
    assert backend_item["id"] == agent_backend.id
    assert backend_item["agent_label"] == agent_backend.agent_label
    assert backend_item["tool_family"] == agent_backend.tool_family
    assert backend_item["created_at"] is not None
    assert backend_item["roles"] == []

    frontend_item = by_label[agent_frontend.agent_label]
    assert frontend_item["id"] == agent_frontend.id
    assert frontend_item["agent_label"] == agent_frontend.agent_label
    assert frontend_item["tool_family"] is None
    assert frontend_item["created_at"] is not None
    assert frontend_item["roles"] == []


async def test_list_all_agents_returns_200_with_empty_list_when_no_agents(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/agents")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_all_agents_returns_200_with_assigned_roles(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    backend_role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
    )
    frontend_role = await TargetRoleFactory.create(
        db_session,
        role_key="frontend",
        role_label="Frontend",
    )
    agent_with_roles = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-with-roles",
        tool_family="backend",
    )
    agent_without_roles = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-without-roles",
        tool_family=None,
    )
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=agent_with_roles.id,
        target_role_id=backend_role.id,
        agent_identity=agent_with_roles,
        target_role=backend_role,
    )
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=agent_with_roles.id,
        target_role_id=frontend_role.id,
        agent_identity=agent_with_roles,
        target_role=frontend_role,
    )

    response = await client.get("/api/v1/ui/agents")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2

    by_label = {item["agent_label"]: item for item in payload}

    with_roles_item = by_label[agent_with_roles.agent_label]
    assert with_roles_item["id"] == agent_with_roles.id
    roles = with_roles_item["roles"]
    assert len(roles) == 2
    role_keys = {role["role_key"] for role in roles}
    role_labels = {role["role_label"] for role in roles}
    assert role_keys == {"backend", "frontend"}
    assert role_labels == {"Backend", "Frontend"}

    without_roles_item = by_label[agent_without_roles.agent_label]
    assert without_roles_item["id"] == agent_without_roles.id
    assert without_roles_item["roles"] == []
