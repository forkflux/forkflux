from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import TargetRoleFactory


async def test_create_role_returns_201_and_all_db_fields_without_auth(
    client: AsyncClient,
) -> None:
    payload = {"role_key": "backend", "role_label": "Backend"}

    response = await client.post("/api/v1/ui/agents/roles", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["role_key"] == "backend"
    assert body["role_label"] == "Backend"
    assert body["created_at"] is not None


async def test_create_role_returns_422_when_role_key_already_exists(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )

    payload = {"role_key": "admin", "role_label": "Administrator"}

    response = await client.post("/api/v1/ui/agents/roles", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["body", "role_key"]
    assert detail[0]["type"] == "target_role.conflict"
    assert detail[0]["input"] == "admin"


async def test_create_role_returns_422_when_required_fields_missing(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/ui/agents/roles", json={})

    assert response.status_code == 422
    locs = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "role_key") in locs
    assert ("body", "role_label") in locs


async def test_create_role_returns_422_when_fields_are_empty_strings(
    client: AsyncClient,
) -> None:
    payload = {"role_key": "", "role_label": ""}

    response = await client.post("/api/v1/ui/agents/roles", json=payload)

    assert response.status_code == 422
    locs = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "role_key") in locs
    assert ("body", "role_label") in locs
