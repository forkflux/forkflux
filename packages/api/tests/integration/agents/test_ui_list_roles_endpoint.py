from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import TargetRoleFactory


async def test_list_roles_returns_200_and_all_db_fields_without_auth(
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

    response = await client.get("/api/v1/ui/agents/roles")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2

    by_role_key = {item["role_key"]: item for item in payload}

    admin_item = by_role_key[role_admin.role_key]
    assert admin_item["id"] == role_admin.id
    assert admin_item["role_key"] == role_admin.role_key
    assert admin_item["role_label"] == role_admin.role_label
    assert admin_item["created_at"] is not None

    viewer_item = by_role_key[role_viewer.role_key]
    assert viewer_item["id"] == role_viewer.id
    assert viewer_item["role_key"] == role_viewer.role_key
    assert viewer_item["role_label"] == role_viewer.role_label
    assert viewer_item["created_at"] is not None


async def test_list_roles_returns_200_with_empty_list_when_no_roles(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/agents/roles")

    assert response.status_code == 200
    assert response.json() == []
