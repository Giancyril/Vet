import pytest
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "AI Code Reviewer API"
        assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_root_endpoint():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "AI Code Reviewer API"
        assert data["docs_url"] == "/api/v1/docs"
