from unittest.mock import AsyncMock, MagicMock
import pytest
from app.devices.services import DeviceService


class TestDeviceService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        m.db = AsyncMock()
        return m

    async def test_list_devices(self, repo):
        svc = DeviceService(repo)
        items, total = await svc.list_devices()
        assert items == []
        assert total == 0
        repo.list_all.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_list_devices_paginated(self, repo):
        svc = DeviceService(repo)
        await svc.list_devices(skip=10, limit=20)
        repo.list_all.assert_called_once_with(skip=10, limit=20)

    async def test_get_device_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = DeviceService(repo)
        result = await svc.get_device(1)
        assert result is fake
        repo.get_by_id.assert_called_once_with(1)

    async def test_get_device_not_found(self, repo):
        svc = DeviceService(repo)
        result = await svc.get_device(999)
        assert result is None

    async def test_search_devices_empty_criteria(self, repo):
        svc = DeviceService(repo)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        result = await svc.search_devices(MagicMock(criteria=[], conjunction="AND"))
        assert result == []

    async def test_search_devices_with_criteria(self, repo):
        device = MagicMock(spec=["id", "name", "status"])
        device.id = 1
        device.name = "MacBook"
        device.status = "Online"
        svc = DeviceService(repo)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [device]
        repo.db.execute = AsyncMock(return_value=mock_result)
        result = await svc.search_devices(MagicMock(
            criteria=[{"field": "status", "operator": "is", "value": "Online"}],
            conjunction="AND",
        ))
        assert len(result) == 1
        assert result[0].name == "MacBook"
