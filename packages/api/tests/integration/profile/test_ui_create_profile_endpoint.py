from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import ProfileFactory


async def test_create_profile_returns_201_and_is_onboarded_true_when_table_empty(
    client: AsyncClient,
) -> None:
    payload = {"is_onboarded": True}

    response = await client.post("/api/v1/ui/profile", json=payload)

    assert response.status_code == 201
    assert response.json() == {"is_onboarded": True}


async def test_create_profile_returns_201_and_is_onboarded_false_when_table_empty(
    client: AsyncClient,
) -> None:
    payload = {"is_onboarded": False}

    response = await client.post("/api/v1/ui/profile", json=payload)

    assert response.status_code == 201
    assert response.json() == {"is_onboarded": False}


async def test_create_profile_returns_422_when_profile_already_exists(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await ProfileFactory.create(db_session, is_onboarded=True)

    payload = {"is_onboarded": False}

    response = await client.post("/api/v1/ui/profile", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["body", "is_onboarded"]
    assert detail[0]["type"] == "profile.already_exists"
    assert detail[0]["input"] is False


async def test_create_profile_returns_422_when_is_onboarded_missing(
    client: AsyncClient,
) -> None:
    response = await client.post("/api/v1/ui/profile", json={})

    assert response.status_code == 422
    locs = {tuple(item["loc"]) for item in response.json()["detail"]}
    assert ("body", "is_onboarded") in locs
