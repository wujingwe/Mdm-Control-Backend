from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.commands.services import CommandService
from app.commands.schemas import CommandCreate
from app.common.enums import CommandType


class TestCommandService:
    @pytest.fixture
    def repo(self) -> None:
        m = MagicMock()
        m.create = AsyncMock(
            return_value=MagicMock(id=1, device_id=1, command_type=CommandType.LOCK)
        )
        m.get_by_id = AsyncMock(return_value=None)
        m.list_all = AsyncMock(return_value=[])
        m.count_all = AsyncMock(return_value=0)
        m.list_for_device = AsyncMock(return_value=[])
        m.count_for_device = AsyncMock(return_value=0)
        m.mark_sent = AsyncMock(return_value=MagicMock(id=1))
        m.cancel = AsyncMock(return_value=None)
        return m

    async def test_trigger_command_success(self, repo: MagicMock) -> None:
        svc = CommandService(repo)
        data = CommandCreate(command_type=CommandType.LOCK)
        with patch("app.commands.services.rabbitmq_producer") as mock_producer:
            mock_producer.publish_device_command = AsyncMock(return_value="msg-123")
            result = await svc.trigger_command(device_id=1, data=data, created_by=1)
            assert result["command"].id == 1
            assert result["message_id"] == "msg-123"
            repo.create.assert_called_once_with(1, data, 1)
            mock_producer.publish_device_command.assert_called_once()

    async def test_trigger_command_publish_fails(self, repo: MagicMock) -> None:
        svc = CommandService(repo)
        data = CommandCreate(command_type=CommandType.LOCK)
        with patch("app.commands.services.rabbitmq_producer") as mock_producer:
            mock_producer.publish_device_command = AsyncMock(
                side_effect=RuntimeError("MQ down")
            )
            result = await svc.trigger_command(device_id=1, data=data)
            assert result["message_id"] is None
            repo.mark_sent.assert_not_called()

    async def test_get_command(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = CommandService(repo)
        result = await svc.get_command(1)
        assert result is fake

    async def test_list_commands(self, repo: MagicMock) -> None:
        svc = CommandService(repo)
        items, total = await svc.list_commands()
        assert items == []
        assert total == 0
        repo.list_all.assert_called_once_with(skip=0, limit=100)

    async def test_list_device_commands(self, repo: MagicMock) -> None:
        svc = CommandService(repo)
        items, total = await svc.list_device_commands(1, skip=5, limit=10)
        assert items == []
        assert total == 0
        repo.list_for_device.assert_called_once_with(1, skip=5, limit=10)

    async def test_cancel_command(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.cancel = AsyncMock(return_value=fake)
        svc = CommandService(repo)
        result = await svc.cancel_command(1)
        assert result is fake

    async def test_cancel_command_not_cancellable(self, repo: MagicMock) -> None:
        repo.cancel = AsyncMock(return_value=None)
        svc = CommandService(repo)
        result = await svc.cancel_command(1)
        assert result is None
