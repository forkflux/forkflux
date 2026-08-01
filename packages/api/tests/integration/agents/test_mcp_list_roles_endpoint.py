import hashlib
from typing import Generator

import pytest
from forkflux_api.config import Settings, get_settings
from forkflux_api.main import app
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentApiTokenFactory, AgentIdentityFactory, TargetRoleFactory

SHARED_API_KEY = "test-shared-api-key"

AUTH_FAILURE_DETAIL = "Invalid authentication credentials (either Bearer token or API key required)"


@pytest.fixture(autouse=True)
def shared_api_key_settings() -> Generator[None, None, None]:
    previous_override = app.dependency_overrides.get(get_settings)
    app.dependency_overrides[get_settings] = lambda: Settings(shared_api_key=SHARED_API_KEY)
    try:
        yield
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = previous_override


async def test_list_roles_returns_200_and_roles_with_valid_shared_api_key(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
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

    response = await client.get(
        "/api/v1/mcp/agents/roles",
        headers={"Authorization": f"Bearer {SHARED_API_KEY}"},
    )

    assert response.status_code == 200
    assert {(item["role_key"], item["role_label"]) for item in response.json()} == {
        (role_admin.role_key, role_admin.role_label),
        (role_viewer.role_key, role_viewer.role_label),
    }


async def test_list_roles_returns_200_and_roles_with_valid_agent_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-roles-agent-token"
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


async def test_list_roles_returns_401_when_credentials_are_missing(client: AsyncClient) -> None:
    response = await client.get("/api/v1/mcp/agents/roles")

    assert response.status_code == 401
    assert response.json() == {"detail": AUTH_FAILURE_DETAIL}


async def test_list_roles_returns_401_for_invalid_credentials(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/mcp/agents/roles",
        headers={"Authorization": "Bearer invalid-shared-api-key"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": AUTH_FAILURE_DETAIL}
    assert response.headers["www-authenticate"] == "Bearer"
