from app.devices.schemas import Certificate, Network, Wifi


class TestDevicesAPI:
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_get_device_not_found(self, client):
        resp = await client.get("/api/v1/devices/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Device not found"

    async def test_search_devices(self, client):
        resp = await client.post("/api/v1/devices/search", json={"criteria": []})
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_device_response_shape(self, client, db_session):
        from app.devices.repositories import DeviceRepository
        repo = DeviceRepository(db_session)
        device = await repo.create({
            "name": "MacBook",
            "serial_number": "SN-API-001",
            "os_version": "15.0",
            "connection_status": "Online",
            "enrollment_status": "Enrolled",
            "network": Network(wifi=Wifi(ssid="Office")),
            "certificates": [Certificate(common_name="example.com")],
        })
        resp = await client.get(f"/api/v1/devices/{device.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["serial_number"] == "SN-API-001"
        assert body["connection_status"] == "Online"
        assert body["enrollment_status"] == "Enrolled"
        assert "created_at" in body
        assert "updated_at" in body
        assert "last_enrolled_at" in body
        assert body["network"]["wifi"]["ssid"] == "Office"
        assert body["certificates"][0]["common_name"] == "example.com"


class TestSmartGroupsAPI:
    BASE = "/api/v1/smart-groups"

    async def test_crud_flow(self, client):
        create = await client.post(self.BASE, json={
            "name": "Smart Group A",
            "description": "desc",
        })
        assert create.status_code == 201
        gid = create.json()["id"]
        assert create.json()["name"] == "Smart Group A"

        get = await client.get(f"{self.BASE}/{gid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Smart Group A"

        update = await client.put(f"{self.BASE}/{gid}", json={"name": "Smart Group B"})
        assert update.status_code == 200
        assert update.json()["name"] == "Smart Group B"

        delete = await client.delete(f"{self.BASE}/{gid}")
        assert delete.status_code == 200

        get2 = await client.get(f"{self.BASE}/{gid}")
        assert get2.status_code == 404

    async def test_list(self, client):
        await client.post(self.BASE, json={"name": "SG1"})
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1
        assert all(g["name"] is not None for g in data["items"])

    async def test_update_empty_body(self, client):
        create = await client.post(self.BASE, json={"name": "G"})
        gid = create.json()["id"]
        resp = await client.put(f"{self.BASE}/{gid}", json={})
        assert resp.status_code == 400


class TestStaticGroupsAPI:
    BASE = "/api/v1/static-groups"

    async def test_crud_flow(self, client, db_session):
        from app.devices.models import Device

        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev3 = Device(name="D3", serial_number="SN003", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()

        create = await client.post(self.BASE, json={
            "name": "Static Group A",
            "description": "desc",
            "device_serial_numbers": ["SN001", "SN002"],
        })
        assert create.status_code == 201
        gid = create.json()["id"]
        assert create.json()["name"] == "Static Group A"
        assert set(create.json()["device_serial_numbers"]) == {"SN001", "SN002"}

        get = await client.get(f"{self.BASE}/{gid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Static Group A"
        assert set(get.json()["device_serial_numbers"]) == {"SN001", "SN002"}

        update = await client.put(f"{self.BASE}/{gid}", json={
            "name": "Static Group B",
            "device_serial_numbers": ["SN003"],
        })
        assert update.status_code == 200
        assert update.json()["name"] == "Static Group B"
        assert update.json()["device_serial_numbers"] == ["SN003"]

        delete = await client.delete(f"{self.BASE}/{gid}")
        assert delete.status_code == 200

        get2 = await client.get(f"{self.BASE}/{gid}")
        assert get2.status_code == 404

    async def test_list_distinct(self, client):
        await client.post(self.BASE, json={"name": "Static1"})
        await client.post("/api/v1/smart-groups", json={"name": "Smart1"})
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1
        assert all(g["name"] is not None for g in data["items"])

    async def test_update_empty_body(self, client):
        create = await client.post(self.BASE, json={"name": "G"})
        gid = create.json()["id"]
        resp = await client.put(f"{self.BASE}/{gid}", json={})
        assert resp.status_code == 400


class TestUsersAPI:
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_get_user_not_found(self, client):
        resp = await client.get("/api/v1/users/999")
        assert resp.status_code == 404

    async def test_get_by_email_not_found(self, client):
        resp = await client.get("/api/v1/users/by-email/nobody@example.com")
        assert resp.status_code == 404


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
