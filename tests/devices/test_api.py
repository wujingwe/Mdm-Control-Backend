from app.devices.schemas import Certificate, DeviceUpdate, Network, Wifi
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestDevicesAPI:
    async def test_list_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_returns_multiple(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        await repo.create(
            {
                "name": "A",
                "serial_number": "SN-A",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )
        await repo.create(
            {
                "name": "B",
                "serial_number": "SN-B",
                "os_version": "15.0",
                "connection_status": "Disconnected",
                "status": "Enrolled",
            }
        )
        resp = await client.get("/api/v1/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        for i in range(5):
            await repo.create(
                {
                    "name": f"Dev{i}",
                    "serial_number": f"SN-{i:03d}",
                    "os_version": "15.0",
                    "connection_status": "Connected",
                    "status": "Enrolled",
                }
            )
        resp = await client.get("/api/v1/devices?skip=0&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_pagination_second_page(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        for i in range(5):
            await repo.create(
                {
                    "name": f"Dev{i}",
                    "serial_number": f"SN-{i:03d}",
                    "os_version": "15.0",
                    "connection_status": "Connected",
                    "status": "Enrolled",
                }
            )
        resp = await client.get("/api/v1/devices?skip=3&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_get_device(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-GET-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )
        resp = await client.get(f"/api/v1/devices/{device.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == device.id
        assert body["serial_number"] == "SN-GET-001"

    async def test_get_device_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/devices/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Device not found"

    async def test_device_response_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-API-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
                "network": Network(wifi=Wifi(ssid="Office")),
                "certificates": [Certificate(common_name="example.com")],
            }
        )
        resp = await client.get(f"/api/v1/devices/{device.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["serial_number"] == "SN-API-001"
        assert body["connection_status"] == "Connected"
        assert body["status"] == "Enrolled"
        assert "created_at" in body
        assert "updated_at" in body
        assert "last_enrolled_at" in body
        assert body["network"]["wifi"]["ssid"] == "Office"
        assert body["certificates"][0]["common_name"] == "example.com"

    async def test_device_response_optional_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "Basic",
                "serial_number": "SN-BAS-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )
        resp = await client.get(f"/api/v1/devices/{device.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["battery_status"] is None
        assert body["network"] is None
        assert body["certificates"] is None
        assert body["extension_attributes"] == []

    async def test_update_device(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-UPD-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "connection_status": "Disconnected",
                "battery_status": 50,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connection_status"] == "Disconnected"
        assert body["battery_status"] == 50
        assert body["serial_number"] == "SN-UPD-001"

    async def test_update_device_not_found(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/api/v1/devices/999",
            json={"connection_status": "Disconnected"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Device not found"

    async def test_update_device_network(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-NET-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "network": {
                    "wifi": {"ssid": "NewWifi", "signal_strength": -50},
                    "cellular": {"carrier": "Verizon", "roaming": False},
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["network"]["wifi"]["ssid"] == "NewWifi"
        assert body["network"]["wifi"]["signal_strength"] == -50
        assert body["network"]["cellular"]["carrier"] == "Verizon"
        assert body["network"]["cellular"]["roaming"] is False

    async def test_update_device_clear_network(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository
        from app.devices.schemas import Network, Wifi

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-CN-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
                "network": Network(wifi=Wifi(ssid="Old")),
            }
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"network": None},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["network"] is None

    async def test_update_device_ext_attributes(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository
        from app.extension_attributes.repositories import ExtensionAttributeRepository
        from app.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea = await ea_repo.create(
            ExtensionAttributeCreate(
                name="custom_field",
                data_type="string",
                input_type="Text field",
                created_by=1,
            )
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-EXT-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "extension_attributes": [
                    {
                        "extension_attribute_id": ea.id,
                        "extension_attribute_name": "custom_field",
                        "value": "test_value",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["extension_attributes"]) == 1
        assert body["extension_attributes"][0]["value"] == "test_value"

        get_resp = await client.get(f"/api/v1/devices/{device.id}")
        assert get_resp.status_code == 200
        assert len(get_resp.json()["extension_attributes"]) == 1

    async def test_update_device_clear_ext_attributes(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository
        from app.extension_attributes.repositories import ExtensionAttributeRepository
        from app.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea = await ea_repo.create(
            ExtensionAttributeCreate(
                name="custom_field",
                data_type="string",
                input_type="Text field",
                created_by=1,
            )
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-CLR-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )
        await repo.update(
            device.id,
            DeviceUpdate(
                extension_attributes=[
                    {
                        "extension_attribute_id": ea.id,
                        "extension_attribute_name": "custom_field",
                        "value": "val1",
                    },
                ],
            ),
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"extension_attributes": []},
        )
        assert resp.status_code == 200

        get_resp = await client.get(f"/api/v1/devices/{device.id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["extension_attributes"] == []

    async def test_update_device_certificates(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-CRT-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "certificates": [
                    {"common_name": "new.com", "issuer": "CA2"},
                    {"common_name": "backup.com"},
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["certificates"]) == 2
        assert body["certificates"][0]["common_name"] == "new.com"

    async def test_update_device_clear_certificates(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-CC-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
                "certificates": [Certificate(common_name="old.com")],
            }
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"certificates": None},
        )
        assert resp.status_code == 200
        assert resp.json()["certificates"] is None

    async def test_update_device_multiple_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-MUL-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "connection_status": "Disconnected",
                "status": "Unenrolled",
                "battery_status": 15,
                "total_memory": 16,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connection_status"] == "Disconnected"
        assert body["status"] == "Unenrolled"
        assert body["battery_status"] == 15
        assert body["total_memory"] == 16

    async def test_update_device_invalid_connection_status(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-INV-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"connection_status": "INVALID_STATUS"},
        )
        assert resp.status_code == 422

    async def test_update_device_invalid_status(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-INV-002",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"status": "INVALID_STATUS"},
        )
        assert resp.status_code == 422

    async def test_update_device_empty_body(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        device = await repo.create(
            {
                "name": "MacBook",
                "serial_number": "SN-EMP-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connection_status"] == "Connected"
        assert body["serial_number"] == "SN-EMP-001"


class TestCommandsAPI:
    async def _create_device(self, db_session: AsyncSession) -> None:
        from app.devices.repositories import DeviceRepository

        repo = DeviceRepository(db_session)
        return await repo.create(
            {
                "name": "CmdDevice",
                "serial_number": "SN-CMD-001",
                "os_version": "15.0",
                "connection_status": "Connected",
                "status": "Enrolled",
            }
        )

    async def test_list_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device = await self._create_device(db_session)
        resp = await client.get(f"/api/v1/devices/{device.id}/commands")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_trigger_and_get(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device = await self._create_device(db_session)
        create_resp = await client.post(
            f"/api/v1/devices/{device.id}/commands",
            json={"command_type": "LOCK"},
        )
        assert create_resp.status_code == 201
        cmd = create_resp.json()
        assert cmd["command_type"] == "LOCK"
        assert cmd["status"] == "PENDING"
        command_id = cmd["id"]

        get_resp = await client.get(
            f"/api/v1/devices/{device.id}/commands/{command_id}"
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == command_id

    async def test_trigger_invalid_command_type(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device = await self._create_device(db_session)
        resp = await client.post(
            f"/api/v1/devices/{device.id}/commands",
            json={"command_type": "INVALID_TYPE"},
        )
        assert resp.status_code == 422

    async def test_get_command_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device = await self._create_device(db_session)
        resp = await client.get(f"/api/v1/devices/{device.id}/commands/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Command not found"

    async def test_get_command_wrong_device(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device = await self._create_device(db_session)
        create_resp = await client.post(
            f"/api/v1/devices/{device.id}/commands",
            json={"command_type": "LOCK"},
        )
        command_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/devices/99999/commands/{command_id}")
        assert resp.status_code == 404

    async def test_list_device_commands(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device = await self._create_device(db_session)
        await client.post(
            f"/api/v1/devices/{device.id}/commands", json={"command_type": "LOCK"}
        )
        await client.post(
            f"/api/v1/devices/{device.id}/commands", json={"command_type": "UNLOCK"}
        )
        resp = await client.get(f"/api/v1/devices/{device.id}/commands")
        data = resp.json()
        assert data["total"] == 2

    async def test_list_device_commands_pagination(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device = await self._create_device(db_session)
        for _ in range(5):
            await client.post(
                f"/api/v1/devices/{device.id}/commands", json={"command_type": "LOCK"}
            )
        resp = await client.get(f"/api/v1/devices/{device.id}/commands?skip=0&limit=2")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
