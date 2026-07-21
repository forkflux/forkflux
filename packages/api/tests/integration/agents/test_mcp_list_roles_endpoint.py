import hashlib

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentApiTokenFactory, AgentIdentityFactory, TargetRoleFactory


async def test_list_roles_returns_200_and_roles_with_valid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-roles-token"
    role_admin = await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    role_viewer = await TargetRoleFactory.create(
        db_session,
        role_key="viewer",
        role_label="Viewer",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-list-roles",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=identity.id,
        is_active=True,
    )

    response = await client.get(
        "/api/v1/mcp/agents/roles",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert {(item["role_key"], item["role_label"]) for item in response.json()} == {
        (role_admin.role_key, role_admin.role_label),
        (role_viewer.role_key, role_viewer.role_label),
    }


async def test_list_roles_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.get("/api/v1/mcp/agents/roles")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_list_roles_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    valid_raw_token = "some-other-valid-token"
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-invalid-token",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(valid_raw_token.encode()).hexdigest(),
        agent_id=identity.id,
        is_active=True,
    )

    response = await client.get(
        "/api/v1/mcp/agents/roles",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"
