import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(unauthenticated_client: AsyncClient):
    response = await unauthenticated_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

