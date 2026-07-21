from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import ProfileFactory


async def test_get_profile_returns_200_and_is_onboarded_true_when_row_exists(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await ProfileFactory.create(db_session, is_onboarded=True)

    response = await client.get("/api/v1/ui/profile")

    assert response.status_code == 200
    assert response.json() == {"is_onboarded": True}


async def test_get_profile_returns_200_and_is_onboarded_false_when_row_exists(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await ProfileFactory.create(db_session, is_onboarded=False)

    response = await client.get("/api/v1/ui/profile")

    assert response.status_code == 200
    assert response.json() == {"is_onboarded": False}


async def test_get_profile_returns_200_and_is_onboarded_false_when_table_empty(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/ui/profile")

    assert response.status_code == 200
    assert response.json() == {"is_onboarded": False}
