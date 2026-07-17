import hashlib

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import (
    AgentApiTokenFactory,
    AgentIdentityFactory,
    AgentIdentityRoleFactory,
    TargetRoleFactory,
)


async def test_list_my_roles_returns_200_and_only_assigned_roles(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-my-roles-token"
    role_assigned = await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    await TargetRoleFactory.create(
        db_session,
        role_key="viewer",
        role_label="Viewer",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-list-my-roles",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=identity.id,
        is_active=True,
    )
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=identity.id,
        target_role_id=role_assigned.id,
    )

    response = await client.get(
        "/api/v1/agents/me/roles",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert {(item["role_key"], item["role_label"]) for item in response.json()} == {
        (role_assigned.role_key, role_assigned.role_label),
    }


async def test_list_my_roles_returns_200_and_empty_list_when_no_roles_assigned(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-my-roles-no-roles-token"
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-no-roles",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=identity.id,
        is_active=True,
    )

    response = await client.get(
        "/api/v1/agents/me/roles",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_list_my_roles_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.get("/api/v1/agents/me/roles")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_list_my_roles_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    valid_raw_token = "some-other-valid-token-for-my-roles"
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-invalid-token-my-roles",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(valid_raw_token.encode()).hexdigest(),
        agent_id=identity.id,
        is_active=True,
    )

    response = await client.get(
        "/api/v1/agents/me/roles",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"
