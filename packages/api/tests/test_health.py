from httpx import AsyncClient


async def test_health_endpoint_returns_no_content(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 204
    assert response.content == b""
