from unittest.mock import patch

from httpx import AsyncClient


class TestHealth:
    async def test_liveness(self, client: AsyncClient) -> None:
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_readiness(self, client: AsyncClient) -> None:
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert data["rabbitmq"] == "disconnected"

    async def test_readiness_db_error(self, client: AsyncClient) -> None:
        with patch("app.main.rabbitmq_producer") as mock_producer:
            mock_producer.healthy = True
            resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["database"] == "ok"
        assert data["rabbitmq"] == "ok"

    async def test_health_legacy(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert data["rabbitmq"] == "disconnected"
