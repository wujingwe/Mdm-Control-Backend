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


class TestCommandsAPI:
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/devices/1/commands")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_trigger_and_get(self, client):
        create_resp = await client.post(
            "/api/v1/devices/1/commands",
            json={"command_type": "LOCK"},
        )
        assert create_resp.status_code == 201
        cmd = create_resp.json()
        assert cmd["command_type"] == "LOCK"
        assert cmd["status"] == "PENDING"
        command_id = cmd["id"]

        get_resp = await client.get(f"/api/v1/devices/1/commands/{command_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == command_id

    async def test_get_not_found(self, client):
        resp = await client.get("/api/v1/devices/1/commands/999")
        assert resp.status_code == 404

    async def test_cancel_pending(self, client):
        create_resp = await client.post(
            "/api/v1/devices/1/commands",
            json={"command_type": "LOCK"},
        )
        command_id = create_resp.json()["id"]

        cancel_resp = await client.delete(f"/api/v1/devices/1/commands/{command_id}")
        assert cancel_resp.status_code == 200

    async def test_list_device_commands(self, client):
        await client.post("/api/v1/devices/1/commands", json={"command_type": "LOCK"})
        await client.post("/api/v1/devices/1/commands", json={"command_type": "UNLOCK"})
        resp = await client.get("/api/v1/devices/1/commands")
        data = resp.json()
        assert data["total"] == 2
