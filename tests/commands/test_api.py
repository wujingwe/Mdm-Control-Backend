from unittest.mock import AsyncMock, patch
from app.common.enums import ConnectionStatus, EnrollmentStatus
from app.devices.models import Device
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock


async def _create_device(client: AsyncClient, db_session: AsyncSession) -> None:
    device = Device(
        name="Test Device",
        serial_number="SER001",
        os_version="15.0",
        connection_status=ConnectionStatus.ONLINE,
        enrollment_status=EnrollmentStatus.ENROLLED,
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


class TestCommandsAPI:
    BASE = "/api/v1/devices"

    @patch("app.commands.services.rabbitmq_producer")
    async def test_trigger_and_list(self, mock_producer: MagicMock, client: AsyncClient, db_session: AsyncSession) -> None:
        mock_producer.publish_device_command = AsyncMock(return_value="msg-123")
        device = await _create_device(client, db_session)

        create = await client.post(
            f"{self.BASE}/{device.id}/commands",
            json={
                "command_type": "LOCK",
            },
        )
        assert create.status_code == 201
        cid = create.json()["id"]
        assert create.json()["status"] == "SENT"

        get = await client.get(f"{self.BASE}/{device.id}/commands/{cid}")
        assert get.status_code == 200
        assert get.json()["device_id"] == device.id

        list_resp = await client.get(f"{self.BASE}/{device.id}/commands")
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] >= 1

    @patch("app.commands.services.rabbitmq_producer")
    async def test_cancel(self, mock_producer: MagicMock, client: AsyncClient, db_session: AsyncSession) -> None:
        mock_producer.publish_device_command = AsyncMock(return_value="msg-123")
        device = await _create_device(client, db_session)

        create = await client.post(
            f"{self.BASE}/{device.id}/commands",
            json={
                "command_type": "LOCK",
            },
        )
        cid = create.json()["id"]
        resp = await client.delete(f"{self.BASE}/{device.id}/commands/{cid}")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Command cancelled"

    async def test_get_not_found(self, client: AsyncClient, db_session: AsyncSession) -> None:
        device = await _create_device(client, db_session)
        resp = await client.get(f"{self.BASE}/{device.id}/commands/999")
        assert resp.status_code == 404
