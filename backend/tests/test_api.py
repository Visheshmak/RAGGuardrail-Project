import pytest

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_ready_check(client):
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "dependencies" in response.json()

