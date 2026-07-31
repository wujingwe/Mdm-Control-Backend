from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.domains.commands.services import CommandService
from app.domains.commands.schemas import CommandCreate
from app.domains.commands.enums import CommandStatus, CommandType


class TestCommandService:
    @pytest.fixture
    def repo(self) -> None:
        m = MagicMock()
        m.create = AsyncMock(return_value=MagicMock(id=1, device_id=1, command_type=CommandType.LOCK))
        m.get_by_id = AsyncMock(return_value=None)
        m.list = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.list_for_device = AsyncMock(return_value=[])
        m.count_for_device = AsyncMock(return_value=0)
        m.mark_sent = AsyncMock(return_value=MagicMock(id=1))
        m.update_status = AsyncMock(return_value=MagicMock(id=1, device_id=1, status=CommandStatus.COMPLETED))
        m.cancel = AsyncMock(return_value=None)
        return m

    @pytest.fixture
    def device_repo(self) -> None:
        m = MagicMock()
        m.get_serial_number = AsyncMock(return_value="SER001")
        return m

    async def test_trigger_command_success(self, repo: MagicMock, device_repo: MagicMock) -> None:
        svc = CommandService(repo, device_repo)
        data = CommandCreate(command_type=CommandType.LOCK)
        with patch("app.domains.commands.services.rabbitmq_producer") as mock_producer:
            mock_producer.publish_device_command = AsyncMock(return_value="msg-123")
            result = await svc.trigger_command(device_id=1, data=data, created_by=1)
            assert result["command"].id == 1
            assert result["message_id"] == "msg-123"
            repo.create.assert_called_once_with(1, data, 1)
            device_repo.get_serial_number.assert_called_once_with(1)
            mock_producer.publish_device_command.assert_called_once_with(
                serial_number="SER001",
                command_id=1,
                command_type="LOCK",
                parameters={},
            )

    async def test_trigger_command_publish_fails(self, repo: MagicMock, device_repo: MagicMock) -> None:
        svc = CommandService(repo, device_repo)
        data = CommandCreate(command_type=CommandType.LOCK)
        with patch("app.domains.commands.services.rabbitmq_producer") as mock_producer:
            mock_producer.publish_device_command = AsyncMock(side_effect=RuntimeError("MQ down"))
            result = await svc.trigger_command(device_id=1, data=data, created_by=1)
            assert result["message_id"] is None
            repo.mark_sent.assert_not_called()

    async def test_trigger_command_device_not_found(self, repo: MagicMock, device_repo: MagicMock) -> None:
        device_repo.get_serial_number = AsyncMock(return_value=None)
        svc = CommandService(repo, device_repo)
        data = CommandCreate(command_type=CommandType.LOCK)
        with patch("app.domains.commands.services.rabbitmq_producer") as mock_producer:
            result = await svc.trigger_command(device_id=999, data=data, created_by=1)
            assert result["message_id"] is None
            mock_producer.publish_device_command.assert_not_called()

    async def test_get_command(self, repo: MagicMock, device_repo: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = CommandService(repo, device_repo)
        result = await svc.get_command(1)
        assert result is fake

    async def test_update_status(self, repo: MagicMock, device_repo: MagicMock) -> None:
        svc = CommandService(repo, device_repo)
        result = await svc.update_status(1, CommandStatus.COMPLETED, "done")
        assert result.status == CommandStatus.COMPLETED
        repo.update_status.assert_called_once_with(1, CommandStatus.COMPLETED, "done")

    async def test_list_commands(self, repo: MagicMock, device_repo: MagicMock) -> None:
        svc = CommandService(repo, device_repo)
        items, total = await svc.list_commands()
        assert items == []
        assert total == 0
        repo.list.assert_called_once_with(skip=0, limit=100)

    async def test_list_device_commands(self, repo: MagicMock, device_repo: MagicMock) -> None:
        svc = CommandService(repo, device_repo)
        items, total = await svc.list_device_commands(1, skip=5, limit=10)
        assert items == []
        assert total == 0
        repo.list_for_device.assert_called_once_with(1, skip=5, limit=10)
