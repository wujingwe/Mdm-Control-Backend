import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.common.enums import CommandStatus


class TestProcessProfileStatusMessage:
    @pytest.mark.asyncio
    @patch("app.messaging.consumer.send_validation_webhook", new_callable=AsyncMock)
    @patch("app.messaging.consumer.async_session")
    async def test_profile_status_reported_updates_assignment(
        self, mock_session_factory, mock_webhook
    ):
        from app.messaging.consumer import process_profile_status_message

        mock_assignment = MagicMock()
        mock_assignment.profile_id = 1
        mock_assignment.device_id = 100

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_assignment

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        data = {
            "event_type": "profile.status.reported",
            "profile_id": 1,
            "device_id": 100,
            "status": "APPLIED",
        }
        await process_profile_status_message(data)
        mock_webhook.assert_called_once_with("100")
        assert mock_assignment.status == "APPLIED"

    @pytest.mark.asyncio
    @patch("app.messaging.consumer.send_validation_webhook", new_callable=AsyncMock)
    async def test_profile_status_ignored_event(self, mock_webhook):
        from app.messaging.consumer import process_profile_status_message

        data = {"event_type": "other.event"}
        await process_profile_status_message(data)
        mock_webhook.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.messaging.consumer.send_validation_webhook", new_callable=AsyncMock)
    async def test_profile_status_invalid_status(self, mock_webhook):
        from app.messaging.consumer import process_profile_status_message

        data = {
            "event_type": "profile.status.reported",
            "profile_id": 1,
            "device_id": 100,
            "status": "InvalidStatus",
        }
        await process_profile_status_message(data)
        mock_webhook.assert_not_called()


class TestProcessDeviceCommandStatus:
    @pytest.mark.asyncio
    @patch("app.messaging.consumer.async_session")
    async def test_completed_updates_command(self, mock_session_factory):
        from app.messaging.consumer import process_device_command_status

        mock_cmd = MagicMock()
        mock_cmd.id = 999
        mock_cmd.status = CommandStatus.SENT

        mock_result = MagicMock()
        mock_result.get.return_value = mock_cmd

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_cmd)
        mock_db.commit = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        data = {
            "event_type": "device.command.completed",
            "command_id": 999,
            "device_serial_number": "SER001",
        }
        await process_device_command_status(data)
        assert mock_cmd.status == CommandStatus.COMPLETED
        assert mock_cmd.completed_at is not None

    @pytest.mark.asyncio
    async def test_missing_command_id(self):
        from app.messaging.consumer import process_device_command_status

        await process_device_command_status({"event_type": "device.command.completed"})

    @pytest.mark.asyncio
    async def test_unknown_event_type(self):
        from app.messaging.consumer import process_device_command_status

        await process_device_command_status(
            {"event_type": "unknown.event", "command_id": 1}
        )


class TestCompositeHandler:
    @pytest.mark.asyncio
    @patch(
        "app.messaging.consumer.process_profile_status_message", new_callable=AsyncMock
    )
    async def test_routes_profile_event(self, mock_profile):
        from app.messaging.consumer import composite_handler

        data = {"event_type": "profile.status.reported"}
        await composite_handler(data)
        mock_profile.assert_called_once_with(data)

    @pytest.mark.asyncio
    @patch(
        "app.messaging.consumer.process_device_command_status", new_callable=AsyncMock
    )
    async def test_routes_command_event(self, mock_cmd):
        from app.messaging.consumer import composite_handler

        data = {"event_type": "device.command.completed"}
        await composite_handler(data)
        mock_cmd.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_ignores_unknown_event(self):
        from app.messaging.consumer import composite_handler

        await composite_handler({"event_type": "other.event"})
