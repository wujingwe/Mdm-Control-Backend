from unittest.mock import AsyncMock, MagicMock
import pytest
from app.devices.services import DeviceService
from app.devices.schemas import DeviceSearchCriteria, DeviceUpdate


class TestDeviceService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        m.update = AsyncMock(return_value=None)
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

    async def test_update_device_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        repo.update = AsyncMock(return_value=fake)
        svc = DeviceService(repo)
        data = DeviceUpdate(connection_status="Offline")
        result = await svc.update_device(1, data)
        assert result is fake
        repo.get_by_id.assert_called_once_with(1)
        repo.update.assert_called_once_with(1, data)

    async def test_update_device_not_found(self, repo):
        repo.get_by_id = AsyncMock(return_value=None)
        svc = DeviceService(repo)
        result = await svc.update_device(999, DeviceUpdate(connection_status="Offline"))
        assert result is None
        repo.update.assert_not_called()

    async def test_search_devices_empty_criteria(self, repo):
        svc = DeviceService(repo)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        result = await svc.search_devices(DeviceSearchCriteria(criteria=[]))
        assert result == []

    async def test_search_devices_is_operator(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["device1"]
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "connection_status", "operator": "is", "value": "Online"}],
                conjunction="AND",
            )
        )
        assert result == ["device1"]

    async def test_search_devices_isNot_operator(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "connection_status", "operator": "isNot", "value": "Offline"}],
                conjunction="AND",
            )
        )
        assert result == []

    async def test_search_devices_like_operator(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "name", "operator": "like", "value": "Mac"}],
                conjunction="AND",
            )
        )
        assert result == []

    async def test_search_devices_notLike_operator(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "name", "operator": "notLike", "value": "Windows"}],
                conjunction="AND",
            )
        )
        assert result == []

    async def test_search_devices_greaterThan_operator(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "battery_status", "operator": "greaterThan", "value": "50"}],
                conjunction="AND",
            )
        )
        assert result == []

    async def test_search_devices_lessThan_operator(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "battery_status", "operator": "lessThan", "value": "20"}],
                conjunction="AND",
            )
        )
        assert result == []

    async def test_search_devices_and_conjunction(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[
                    {"field": "connection_status", "operator": "is", "value": "Online"},
                    {"field": "enrollment_status", "operator": "is", "value": "Enrolled"},
                ],
                conjunction="AND",
            )
        )
        assert result == []

    async def test_search_devices_or_conjunction(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[
                    {"field": "connection_status", "operator": "is", "value": "Online"},
                    {"field": "connection_status", "operator": "is", "value": "Offline"},
                ],
                conjunction="OR",
            )
        )
        assert result == []

    async def test_search_devices_unknown_field_skipped(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "nonexistent_field", "operator": "is", "value": "x"}],
                conjunction="AND",
            )
        )
        assert result == []

    async def test_search_devices_unknown_operator_uses_default(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "name", "operator": "unknownOp", "value": "x"}],
                conjunction="AND",
            )
        )
        assert result == []

    async def test_search_devices_no_results(self, repo):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.search_devices(
            DeviceSearchCriteria(
                criteria=[{"field": "name", "operator": "is", "value": "NonExistent"}],
                conjunction="AND",
            )
        )
        assert result == []
