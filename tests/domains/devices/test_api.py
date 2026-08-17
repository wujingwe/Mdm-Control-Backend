from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dependencies import get_reconciliation_service
from app.domains.commands.enums import CommandType
from app.domains.commands.repositories import CommandRepository
from app.domains.commands.schemas import CommandCreate
from app.domains.extension_attributes.enums import ExtensionDataType, ExtensionInputType
from app.domains.devices.models import Device
from app.domains.devices.repositories import DeviceRepository
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.devices.schemas import (
    Certificate,
    DeviceCreate,
    DeviceUpdate,
    Network,
    Wifi,
    ExtensionAttributeValueCreate,
)
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.profiles.models import Profile, ProfileAssignment
from app.domains.shared.scope import Scope
from app.main import app
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
from app.domains.extension_attributes.schemas import ExtensionAttributeCreate


class TestDevicesAPI:
    async def test_list_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_returns_multiple(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        await repo.create(
            DeviceCreate(
                name="A",
                serial_number="SN-A",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        await repo.create(
            DeviceCreate(
                name="B",
                serial_number="SN-B",
                os_version="15.0",
                connection_status=ConnectionStatus.DISCONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.get("/api/v1/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_pagination(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        for i in range(5):
            await repo.create(
                DeviceCreate(
                    name=f"Dev{i}",
                    serial_number=f"SN-{i:03d}",
                    os_version="15.0",
                    connection_status=ConnectionStatus.CONNECTED,
                    status=DeviceStatus.ENROLLED,
                )
            )
        resp = await client.get("/api/v1/devices?skip=0&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_pagination_second_page(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        for i in range(5):
            await repo.create(
                DeviceCreate(
                    name=f"Dev{i}",
                    serial_number=f"SN-{i:03d}",
                    os_version="15.0",
                    connection_status=ConnectionStatus.CONNECTED,
                    status=DeviceStatus.ENROLLED,
                )
            )
        resp = await client.get("/api/v1/devices?skip=3&limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_get_device(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-GET-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.get(f"/api/v1/devices/{device.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == device.id
        assert body["serialNumber"] == "SN-GET-001"

    async def test_get_device_not_found(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/devices/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Device not found"

    async def test_device_response_shape(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-API-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
                network=Network(wifi=Wifi(ssid="Office")),
                certificates=[Certificate(common_name="example.com")],
            )
        )
        resp = await client.get(f"/api/v1/devices/{device.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["serialNumber"] == "SN-API-001"
        assert body["connectionStatus"] == "Connected"
        assert body["status"] == "Enrolled"
        assert "createdAt" in body
        assert "updatedAt" in body
        assert "lastEnrolledAt" in body
        assert body["network"]["wifi"]["ssid"] == "Office"
        assert body["certificates"][0]["commonName"] == "example.com"

    async def test_device_response_optional_fields(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="Basic",
                serial_number="SN-BAS-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.get(f"/api/v1/devices/{device.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["batteryStatus"] is None
        assert body["network"] is None
        assert body["certificates"] is None
        assert body["extensionAttributeValues"] == []

    async def test_update_device(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-UPD-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "connectionStatus": "Disconnected",
                "batteryStatus": 50,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connectionStatus"] == "Disconnected"
        assert body["batteryStatus"] == 50
        assert body["serialNumber"] == "SN-UPD-001"

    async def test_update_device_not_found(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/api/v1/devices/999",
            json={"connectionStatus": "Disconnected"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Device not found"

    async def test_update_device_network(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-NET-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "network": {
                    "wifi": {"ssid": "NewWifi", "signalStrength": -50},
                    "cellular": {"carrier": "Verizon", "roaming": False},
                },
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["network"]["wifi"]["ssid"] == "NewWifi"
        assert body["network"]["wifi"]["signalStrength"] == -50
        assert body["network"]["cellular"]["carrier"] == "Verizon"
        assert body["network"]["cellular"]["roaming"] is False

    async def test_update_device_clear_network(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-CN-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
                network=Network(wifi=Wifi(ssid="Old")),
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"network": None},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["network"] is None

    async def test_update_device_ext_attributes(self, client: AsyncClient, db_session: AsyncSession) -> None:
        ea_repo = ExtensionAttributeRepository(db_session)
        ea = await ea_repo.create(
            ExtensionAttributeCreate(
                name="custom_field",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
            ),
            created_by=1,
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-EXT-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "extension_attribute_values": [
                    {
                        "extensionAttributeId": ea.id,
                        "extensionAttributeName": "custom_field",
                        "value": "test_value",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["extensionAttributeValues"]) == 1
        assert body["extensionAttributeValues"][0]["value"] == "test_value"

        get_resp = await client.get(f"/api/v1/devices/{device.id}")
        assert get_resp.status_code == 200
        assert len(get_resp.json()["extensionAttributeValues"]) == 1

    async def test_update_device_clear_ext_attributes(self, client: AsyncClient, db_session: AsyncSession) -> None:
        ea_repo = ExtensionAttributeRepository(db_session)
        ea = await ea_repo.create(
            ExtensionAttributeCreate(
                name="custom_field",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
            ),
            created_by=1,
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-CLR-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        await repo.update(
            device.id,
            DeviceUpdate(
                extension_attribute_values=[
                    ExtensionAttributeValueCreate(
                        extension_attribute_id=ea.id,
                        extension_attribute_name="custom_field",
                        value="val1",
                    ),
                ],
            ),
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"extension_attribute_values": []},
        )
        assert resp.status_code == 200

        get_resp = await client.get(f"/api/v1/devices/{device.id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["extensionAttributeValues"] == []

    async def test_update_device_certificates(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-CRT-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "certificates": [
                    {"commonName": "new.com", "issuer": "CA2"},
                    {"commonName": "backup.com"},
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["certificates"]) == 2
        assert body["certificates"][0]["commonName"] == "new.com"

    async def test_update_device_clear_certificates(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-CC-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
                certificates=[Certificate(common_name="old.com")],
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"certificates": None},
        )
        assert resp.status_code == 200
        assert resp.json()["certificates"] is None

    async def test_update_device_multiple_fields(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-MUL-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={
                "connectionStatus": "Disconnected",
                "status": "Unenrolled",
                "batteryStatus": 15,
                "totalMemory": 16,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connectionStatus"] == "Disconnected"
        assert body["status"] == "Unenrolled"
        assert body["batteryStatus"] == 15
        assert body["totalMemory"] == 16

    async def test_update_device_invalid_connection_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-INV-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"connectionStatus": "INVALID_STATUS"},
        )
        assert resp.status_code == 422

    async def test_update_device_invalid_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-INV-002",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={"status": "INVALID_STATUS"},
        )
        assert resp.status_code == 422

    async def test_update_device_empty_body(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="MacBook",
                serial_number="SN-EMP-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )

        resp = await client.put(
            f"/api/v1/devices/{device.id}",
            json={},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["connectionStatus"] == "Connected"
        assert body["serialNumber"] == "SN-EMP-001"

    async def test_update_device_triggers_reconciler(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="Triggers",
                serial_number="SN-TRG-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )

        reconciliation_service = MagicMock()
        reconciliation_service.recalculate_profiles_for_device = AsyncMock()
        reconciliation_service.recalculate_mobile_apps_for_device = AsyncMock()
        app.dependency_overrides[get_reconciliation_service] = lambda: reconciliation_service
        try:
            resp = await client.put(
                f"/api/v1/devices/{device.id}",
                json={"connectionStatus": "Disconnected"},
            )
        finally:
            app.dependency_overrides.pop(get_reconciliation_service, None)

        assert resp.status_code == 200
        reconciliation_service.recalculate_profiles_for_device.assert_awaited_once_with(device.id)
        reconciliation_service.recalculate_mobile_apps_for_device.assert_awaited_once_with(device.id)

    async def test_update_device_non_trigger_field_skips_reconciler(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="NoTrigger",
                serial_number="SN-NTRG-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )

        reconciliation_service = MagicMock()
        reconciliation_service.recalculate_profiles_for_device = AsyncMock()
        reconciliation_service.recalculate_mobile_apps_for_device = AsyncMock()
        app.dependency_overrides[get_reconciliation_service] = lambda: reconciliation_service
        try:
            resp = await client.put(
                f"/api/v1/devices/{device.id}",
                json={"network": {"wifi": {"ssid": "Guest"}}},
            )
        finally:
            app.dependency_overrides.pop(get_reconciliation_service, None)

        assert resp.status_code == 200
        reconciliation_service.recalculate_profiles_for_device.assert_not_called()


class TestDeviceRegisterReportAPI:
    async def test_register_creates_device(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/devices/SN-REG-001/register",
            json={
                "name": "Pixel 9",
                "osVersion": "15.0",
                "certificates": [{"commonName": "SN-REG-001", "expiry": "2027-01-01T00:00:00Z"}],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["serialNumber"] == "SN-REG-001"
        assert body["status"] == "Enrolled"
        assert body["certificates"][0]["commonName"] == "SN-REG-001"

    async def test_register_idempotent_upsert(self, client: AsyncClient) -> None:
        for _ in range(2):
            resp = await client.post(
                "/api/v1/devices/SN-REG-002/register",
                json={
                    "name": "Pixel 9",
                    "osVersion": "15.0",
                },
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["serialNumber"] == "SN-REG-002"
            assert body["status"] == "Enrolled"

    async def test_register_first_enrollment_triggers_reconciler(self, client: AsyncClient) -> None:
        reconciliation_service = MagicMock()
        reconciliation_service.recalculate_profiles_for_device = AsyncMock()
        reconciliation_service.recalculate_mobile_apps_for_device = AsyncMock()
        app.dependency_overrides[get_reconciliation_service] = lambda: reconciliation_service
        try:
            resp = await client.post(
                "/api/v1/devices/SN-REG-REC1/register",
                json={"name": "Pixel 9", "osVersion": "15.0"},
            )
        finally:
            app.dependency_overrides.pop(get_reconciliation_service, None)

        assert resp.status_code == 200
        device_id = resp.json()["id"]
        reconciliation_service.recalculate_profiles_for_device.assert_awaited_once_with(device_id)
        reconciliation_service.recalculate_mobile_apps_for_device.assert_awaited_once_with(device_id)

    async def test_register_re_enrollment_triggers_reconciler(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        repo = DeviceRepository(db_session)
        existing = await repo.create(
            DeviceCreate(
                name="Old",
                serial_number="SN-REG-REC2",
                os_version="14.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )

        reconciliation_service = MagicMock()
        reconciliation_service.recalculate_profiles_for_device = AsyncMock()
        reconciliation_service.recalculate_mobile_apps_for_device = AsyncMock()
        app.dependency_overrides[get_reconciliation_service] = lambda: reconciliation_service
        try:
            resp = await client.post(
                "/api/v1/devices/SN-REG-REC2/register",
                json={"name": "New Name", "osVersion": "15.0"},
            )
        finally:
            app.dependency_overrides.pop(get_reconciliation_service, None)

        assert resp.status_code == 200
        assert resp.json()["id"] == existing.id
        reconciliation_service.recalculate_profiles_for_device.assert_awaited_once_with(existing.id)
        reconciliation_service.recalculate_mobile_apps_for_device.assert_awaited_once_with(existing.id)

    async def test_register_re_enroll_updates(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        await repo.create(
            DeviceCreate(
                name="Old",
                serial_number="SN-REG-003",
                os_version="14.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.post(
            "/api/v1/devices/SN-REG-003/register",
            json={
                "name": "New Name",
                "osVersion": "15.0",
                "certificates": [{"commonName": "SN-REG-003"}],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "New Name"
        assert body["osVersion"] == "15.0"
        assert body["certificates"][0]["commonName"] == "SN-REG-003"

    async def test_report_in_updates_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Disconnected",
                "status": "Enrolled",
                "batteryStatus": 42,
                "network": {"wifi": {"ssid": "Office"}},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["serialNumber"] == "SN-RPT-001"
        assert body["connectionStatus"] == "Disconnected"
        assert body["batteryStatus"] == 42
        assert body["network"]["wifi"]["ssid"] == "Office"

    async def test_report_in_unknown_serial_is_404(self, client: AsyncClient) -> None:
        resp = await client.put(
            "/api/v1/devices/SN-UNKNOWN/report",
            json={"connectionStatus": "Connected", "status": "Enrolled"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Device not found"

    async def test_report_in_updates_command_status(self, client: AsyncClient, db_session: AsyncSession) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-CMD-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        command_repo = CommandRepository(db_session)
        command = await command_repo.create(
            device.id,
            CommandCreate(command_type=CommandType.RESTART),
            created_by=1,
        )
        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "commands": [
                    {
                        "commandId": command.id,
                        "status": "COMPLETED",
                        "resultMessage": "Restarted cleanly",
                    }
                ],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(command)
        updated = command
        assert updated.status.value == "COMPLETED"
        assert updated.result_message == "Restarted cleanly"
        assert updated.completed_at is not None

    async def test_report_in_command_for_other_device_ignored(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-OTHR-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        other = await device_repo.create(
            DeviceCreate(
                name="Other",
                serial_number="SN-RPT-OTHR-002",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        command_repo = CommandRepository(db_session)
        other_command = await command_repo.create(
            other.id,
            CommandCreate(command_type=CommandType.LOCK),
            created_by=1,
        )
        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "commands": [{"commandId": other_command.id, "status": "COMPLETED"}],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(other_command)
        untouched = other_command
        assert untouched.status.value == "PENDING"

    async def test_report_in_invalid_status_is_422(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-002",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={"status": "INVALID_STATUS"},
        )
        assert resp.status_code == 422

    async def test_report_in_updates_profile_assignment_status(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-PROF-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        profile = Profile(name="Wifi Profile", policy={}, scope=Scope(), created_by=1)
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        assignment = ProfileAssignment(
            profile_id=profile.id,
            device_id=device.id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)

        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "profileAssignments": [
                    {
                        "assignmentId": assignment.id,
                        "status": "APPLIED",
                        "resultMessage": "Profile applied",
                    }
                ],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(assignment)
        assert assignment.status.value == "APPLIED"
        assert assignment.completed_at is not None
        assert assignment.applied_at is not None
        assert assignment.acknowledged_at is None
        assert assignment.last_error is None

    async def test_report_in_assignment_for_other_device_ignored(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-PROF-OTHR-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        other = await device_repo.create(
            DeviceCreate(
                name="Other",
                serial_number="SN-RPT-PROF-OTHR-002",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        profile = Profile(name="Other Profile", policy={}, scope=Scope(), created_by=1)
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        assignment = ProfileAssignment(
            profile_id=profile.id,
            device_id=other.id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)

        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "profileAssignments": [{"assignmentId": assignment.id, "status": "APPLIED"}],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(assignment)
        assert assignment.status.value == "SENT"
        assert assignment.completed_at is None
        assert assignment.acknowledged_at is None

    async def test_report_in_updates_mobile_app_assignment_status(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-APP-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        app = MobileApp(
            name="Outlook",
            enabled=True,
            package_version="4.75.0",
            package_name="com.microsoft.office.outlook",
            scope=Scope(),
            created_by=1,
        )
        db_session.add(app)
        await db_session.commit()
        await db_session.refresh(app)
        assignment = MobileAppAssignment(
            mobile_app_id=app.id,
            device_id=device.id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)

        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "mobileAppAssignments": [
                    {
                        "assignmentId": assignment.id,
                        "status": "APPLIED",
                        "resultMessage": "App installed",
                    }
                ],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(assignment)
        assert assignment.status.value == "APPLIED"
        assert assignment.completed_at is not None
        assert assignment.applied_at is not None
        assert assignment.acknowledged_at is None
        assert assignment.last_error is None

    async def test_report_in_mobile_app_assignment_for_other_device_ignored(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-APP-OTHR-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        other = await device_repo.create(
            DeviceCreate(
                name="Other",
                serial_number="SN-RPT-APP-OTHR-002",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        app = MobileApp(
            name="Other App",
            enabled=True,
            package_version="1.0",
            package_name="com.other.app",
            scope=Scope(),
            created_by=1,
        )
        db_session.add(app)
        await db_session.commit()
        await db_session.refresh(app)
        assignment = MobileAppAssignment(
            mobile_app_id=app.id,
            device_id=other.id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)

        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "mobileAppAssignments": [{"assignmentId": assignment.id, "status": "APPLIED"}],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(assignment)
        assert assignment.status.value == "SENT"
        assert assignment.completed_at is None
        assert assignment.acknowledged_at is None

    async def test_report_in_invalid_profile_assignment_status_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-PROF-INV-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "profileAssignments": [{"assignmentId": 7, "status": "NOPE"}],
            },
        )
        assert resp.status_code == 422

    async def test_report_in_invalid_mobile_app_assignment_status_is_422(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-APP-INV-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "mobileAppAssignments": [{"assignmentId": 9, "status": "NOPE"}],
            },
        )
        assert resp.status_code == 422

    async def test_report_in_profile_assignment_sent_sets_acknowledged_at(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-PROF-SENT-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        profile = Profile(name="Sent Profile", policy={}, scope=Scope(), created_by=1)
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        assignment = ProfileAssignment(
            profile_id=profile.id,
            device_id=device.id,
            status=AssignmentStatus.PENDING,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)

        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "profileAssignments": [{"assignmentId": assignment.id, "status": "SENT"}],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(assignment)
        assert assignment.status.value == "SENT"
        assert assignment.acknowledged_at is not None
        assert assignment.completed_at is None
        assert assignment.last_error is None

    async def test_report_in_profile_assignment_failed_sets_last_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-PROF-FAIL-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        profile = Profile(name="Fail Profile", policy={}, scope=Scope(), created_by=1)
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        assignment = ProfileAssignment(
            profile_id=profile.id,
            device_id=device.id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
        )
        db_session.add(assignment)
        await db_session.commit()
        await db_session.refresh(assignment)

        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "profileAssignments": [
                    {"assignmentId": assignment.id, "status": "FAILED", "resultMessage": "apply error"}
                ],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(assignment)
        assert assignment.status.value == "FAILED"
        assert assignment.last_error == "apply error"
        assert assignment.completed_at is None

    async def test_report_in_combined_commands_and_assignments(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        device_repo = DeviceRepository(db_session)
        device = await device_repo.create(
            DeviceCreate(
                name="Pixel",
                serial_number="SN-RPT-ALL-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        command_repo = CommandRepository(db_session)
        command = await command_repo.create(
            device.id,
            CommandCreate(command_type=CommandType.RESTART),
            created_by=1,
        )
        profile = Profile(name="Combined Profile", policy={}, scope=Scope(), created_by=1)
        db_session.add(profile)
        await db_session.commit()
        await db_session.refresh(profile)
        prof_assignment = ProfileAssignment(
            profile_id=profile.id,
            device_id=device.id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
        )
        db_session.add(prof_assignment)
        app = MobileApp(
            name="Combined App",
            enabled=True,
            package_version="1.0",
            package_name="com.combined.app",
            scope=Scope(),
            created_by=1,
        )
        db_session.add(app)
        await db_session.commit()
        await db_session.refresh(app)
        app_assignment = MobileAppAssignment(
            mobile_app_id=app.id,
            device_id=device.id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
        )
        db_session.add(app_assignment)
        await db_session.commit()
        await db_session.refresh(prof_assignment)
        await db_session.refresh(app_assignment)

        resp = await client.put(
            f"/api/v1/devices/{device.serial_number}/report",
            json={
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "commands": [{"commandId": command.id, "status": "COMPLETED", "resultMessage": "done"}],
                "profileAssignments": [
                    {"assignmentId": prof_assignment.id, "status": "APPLIED", "resultMessage": "applied"}
                ],
                "mobileAppAssignments": [
                    {"assignmentId": app_assignment.id, "status": "APPLIED", "resultMessage": "installed"}
                ],
            },
        )
        assert resp.status_code == 200
        await db_session.refresh(command)
        await db_session.refresh(prof_assignment)
        await db_session.refresh(app_assignment)
        assert command.status.value == "COMPLETED"
        assert command.completed_at is not None
        assert prof_assignment.status.value == "APPLIED"
        assert prof_assignment.completed_at is not None
        assert app_assignment.status.value == "APPLIED"
        assert app_assignment.completed_at is not None


class TestCommandsAPI:
    @staticmethod
    async def _create_device(db_session: AsyncSession) -> Device:
        repo = DeviceRepository(db_session)
        return await repo.create(
            DeviceCreate(
                name="CmdDevice",
                serial_number="SN-CMD-001",
                os_version="15.0",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )

    async def test_list_empty(self, client: AsyncClient, db_session: AsyncSession) -> None:
        device = await self._create_device(db_session)
        resp = await client.get(f"/api/v1/devices/{device.id}/commands")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_trigger_and_get(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", AsyncMock())
        device = await self._create_device(db_session)
        create_resp = await client.post(
            f"/api/v1/devices/{device.id}/commands",
            json={"commandType": "LOCK"},
        )
        assert create_resp.status_code == 201
        cmd = create_resp.json()
        assert cmd["commandType"] == "LOCK"
        assert cmd["status"] == "SENT"
        command_id = cmd["id"]

        get_resp = await client.get(f"/api/v1/devices/{device.id}/commands/{command_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == command_id

    async def test_trigger_invalid_command_type(self, client: AsyncClient, db_session: AsyncSession) -> None:
        device = await self._create_device(db_session)
        resp = await client.post(
            f"/api/v1/devices/{device.id}/commands",
            json={"commandType": "INVALID_TYPE"},
        )
        assert resp.status_code == 422

    async def test_get_command_not_found(self, client: AsyncClient, db_session: AsyncSession) -> None:
        device = await self._create_device(db_session)
        resp = await client.get(f"/api/v1/devices/{device.id}/commands/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Command not found"

    async def test_get_command_wrong_device(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", AsyncMock())
        device = await self._create_device(db_session)
        create_resp = await client.post(
            f"/api/v1/devices/{device.id}/commands",
            json={"commandType": "LOCK"},
        )
        command_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/devices/99999/commands/{command_id}")
        assert resp.status_code == 404

    async def test_list_device_commands(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", AsyncMock())
        device = await self._create_device(db_session)
        await client.post(f"/api/v1/devices/{device.id}/commands", json={"commandType": "LOCK"})
        await client.post(f"/api/v1/devices/{device.id}/commands", json={"commandType": "UNLOCK"})
        resp = await client.get(f"/api/v1/devices/{device.id}/commands")
        data = resp.json()
        assert data["total"] == 2

    async def test_list_device_commands_pagination(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", AsyncMock())
        device = await self._create_device(db_session)
        for _ in range(5):
            await client.post(f"/api/v1/devices/{device.id}/commands", json={"commandType": "LOCK"})
        resp = await client.get(f"/api/v1/devices/{device.id}/commands?skip=0&limit=2")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_trigger_unknown_device(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/devices/999/commands",
            json={"commandType": "CHECK_IN"},
        )
        assert resp.status_code == 201
