from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.exceptions import AgentIdentityNotFoundError
from src.dependencies import get_agent_identity_service
from tests.factories import AgentApiTokenFactory, AgentIdentityFactory, TargetRoleFactory


async def test_get_me_returns_200_and_current_agent_with_valid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-get-me",
        tool_family="internal",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash="valid-get-me-token",
        agent_id=identity.id,
        is_active=True,
    )

    response = await client.get(
        "/v1/agents/me",
        headers={"Authorization": "Bearer valid-get-me-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": identity.id,
        "agent_label": identity.agent_label,
        "role_id": identity.role_id,
        "tool_family": identity.tool_family,
    }


async def test_get_me_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.get("/v1/agents/me")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_get_me_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="auditor",
        role_label="Auditor",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-other-token",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash="some-other-valid-token-for-me",
        agent_id=identity.id,
        is_active=True,
    )

    response = await client.get(
        "/v1/agents/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_get_me_returns_401_when_agent_for_token_cannot_be_loaded(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="support",
        role_label="Support",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-missing",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash="valid-token-agent-missing",
        agent_id=identity.id,
        is_active=True,
    )

    class MissingAgentService:
        async def get_by_id(self, agent_identity_id: int):
            raise AgentIdentityNotFoundError

    app.dependency_overrides[get_agent_identity_service] = lambda: MissingAgentService()
    try:
        response = await client.get(
            "/v1/agents/me",
            headers={"Authorization": "Bearer valid-token-agent-missing"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json() == {"detail": "Agent not found"}
