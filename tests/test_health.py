class TestHealth:
    async def test_liveness(self, client):
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_readiness(self, client):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert isinstance(data["uptime_seconds"], int)
        assert data["database"]["status"] == "ok"
        assert isinstance(data["database"]["latency_ms"], float)
        assert data["rabbitmq"] == "disconnected"

    async def test_health_legacy(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"]["status"] == "ok"
        assert data["version"] == "1.0.0"
