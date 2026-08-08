from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import TargetRoleFactory


async def test_delete_role_returns_204_and_soft_deletes_role_without_auth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
    )

    response = await client.delete(f"/api/v1/ui/agents/roles/{role.id}")

    assert response.status_code == 204
    assert response.content == b""

    await db_session.refresh(role)
    assert role.is_deleted is True


async def test_delete_role_returns_422_when_role_not_found(
    client: AsyncClient,
) -> None:
    response = await client.delete("/api/v1/ui/agents/roles/999_999")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["path", "role_id"]
    assert detail[0]["type"] == "target_role.not_found"
    assert detail[0]["input"] == 999_999


async def test_delete_role_returns_422_for_soft_deleted_role(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    soft_deleted_role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
        is_deleted=True,
    )

    response = await client.delete(f"/api/v1/ui/agents/roles/{soft_deleted_role.id}")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["path", "role_id"]
    assert detail[0]["type"] == "target_role.not_found"
