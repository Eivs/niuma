"""Integration tests for API."""

import pytest
from httpx import AsyncClient, ASGITransport

from niuma.api.main import app


class TestAPI:
    """Test API endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            assert response.json()["name"] == "Niuma"

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    @pytest.mark.asyncio
    async def test_list_agents(self):
        """Test listing agents."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/agents")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
