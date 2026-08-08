from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import TargetRoleFactory


async def test_update_role_returns_200_and_all_db_fields_without_auth(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
    )
    payload = {"role_key": "engineer", "role_label": "Engineer"}

    response = await client.patch(f"/api/v1/ui/agents/roles/{role.id}", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == role.id
    assert body["role_key"] == "engineer"
    assert body["role_label"] == "Engineer"
    assert body["created_at"] is not None


async def test_update_role_returns_422_when_role_key_taken(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
    )
    payload = {"role_key": "admin", "role_label": "Administrator"}

    response = await client.patch(f"/api/v1/ui/agents/roles/{target_role.id}", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["body", "role_key"]
    assert detail[0]["type"] == "target_role.conflict"
    assert detail[0]["input"] == "admin"


async def test_update_role_returns_422_when_role_not_found(
    client: AsyncClient,
) -> None:
    payload = {"role_key": "engineer", "role_label": "Engineer"}

    response = await client.patch("/api/v1/ui/agents/roles/999_999", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["path", "role_id"]
    assert detail[0]["type"] == "target_role.not_found"
    assert detail[0]["input"] == 999_999


async def test_update_role_returns_422_when_required_fields_missing(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
    )

    response = await client.patch(f"/api/v1/ui/agents/roles/{role.id}", json={})

    assert response.status_code == 422
    locs = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "role_key") in locs
    assert ("body", "role_label") in locs


async def test_update_role_returns_422_when_fields_are_empty_strings(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
    )
    payload = {"role_key": "", "role_label": ""}

    response = await client.patch(f"/api/v1/ui/agents/roles/{role.id}", json=payload)

    assert response.status_code == 422
    locs = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "role_key") in locs
    assert ("body", "role_label") in locs


async def test_update_role_does_not_update_soft_deleted_role(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    soft_deleted_role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
        is_deleted=True,
    )
    payload = {"role_key": "engineer", "role_label": "Engineer"}

    response = await client.patch(f"/api/v1/ui/agents/roles/{soft_deleted_role.id}", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["path", "role_id"]
    assert detail[0]["type"] == "target_role.not_found"
