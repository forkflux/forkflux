import hashlib

from forkflux_api.agents.models import AgentApiToken, AgentIdentity, AgentIdentityRole
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import TargetRoleFactory


async def test_create_agent_returns_201_and_persists_agent_roles_and_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    backend_role = await TargetRoleFactory.create(db_session, role_key="backend", role_label="Backend")
    frontend_role = await TargetRoleFactory.create(db_session, role_key="frontend", role_label="Frontend")

    payload = {
        "agent_label": "backend-agent",
        "tool_family": "backend",
        "target_role_ids": [backend_role.id, frontend_role.id],
    }

    response = await client.post("/api/v1/ui/agents", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["agent_id"] is not None
    assert body["agent_label"] == "backend-agent"
    assert body["tool_family"] == "backend"
    assert body["target_role_ids"] == [backend_role.id, frontend_role.id]
    assert body["api_token"]

    agent_id = body["agent_id"]

    agent = (await db_session.execute(select(AgentIdentity).where(AgentIdentity.id == agent_id).options())).scalar_one()
    assert agent.agent_label == "backend-agent"
    assert agent.tool_family == "backend"

    assignments = (
        (
            await db_session.execute(
                select(AgentIdentityRole)
                .where(AgentIdentityRole.agent_identity_id == agent_id)
                .order_by(AgentIdentityRole.target_role_id.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(assignments) == 2
    assert {a.target_role_id for a in assignments} == {backend_role.id, frontend_role.id}

    token_hash = hashlib.sha256(body["api_token"].encode()).hexdigest()
    token = (await db_session.execute(select(AgentApiToken).where(AgentApiToken.token_hash == token_hash))).scalar_one()
    assert token.agent_id == agent_id
    assert token.is_active is True


async def test_create_agent_returns_201_with_none_tool_family(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(db_session, role_key="backend", role_label="Backend")

    payload = {"agent_label": "agent-1", "target_role_ids": [role.id]}

    response = await client.post("/api/v1/ui/agents", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["tool_family"] is None
    assert body["target_role_ids"] == [role.id]


async def test_create_agent_returns_422_when_target_role_ids_empty(
    client: AsyncClient,
) -> None:
    payload = {"agent_label": "agent-1", "tool_family": "backend", "target_role_ids": []}

    response = await client.post("/api/v1/ui/agents", json=payload)

    assert response.status_code == 422
    locs = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "target_role_ids") in locs


async def test_create_agent_returns_422_when_role_ids_do_not_exist(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await TargetRoleFactory.create(db_session, role_key="backend", role_label="Backend")

    payload = {"agent_label": "agent-1", "tool_family": "backend", "target_role_ids": [1, 999_999]}

    response = await client.post("/api/v1/ui/agents", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["body", "target_role_ids"]
    assert detail[0]["type"] == "target_role.not_found"
    assert detail[0]["input"] == [1, 999_999]

    agents = (await db_session.execute(select(AgentIdentity))).scalars().all()
    assert agents == []


async def test_create_agent_returns_422_when_required_fields_missing(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/ui/agents", json={})

    assert response.status_code == 422
    locs = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "agent_label") in locs
    assert ("body", "target_role_ids") in locs


async def test_create_agent_returns_422_when_agent_label_is_empty_string(
    client: AsyncClient,
) -> None:
    payload = {"agent_label": "", "target_role_ids": [1]}

    response = await client.post("/api/v1/ui/agents", json=payload)

    assert response.status_code == 422
    locs = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "agent_label") in locs
