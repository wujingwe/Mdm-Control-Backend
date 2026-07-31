from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.devices.schemas import DeviceUpdate
from app.domains.devices.services import DeviceService


class TestDeviceService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        m = MagicMock()
        m.list = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        m.update = AsyncMock(return_value=None)
        m.db = AsyncMock()
        return m

    @pytest.fixture
    def reconciliation_service(self) -> MagicMock:
        m = MagicMock()
        m.recalculate_profiles_for_device = AsyncMock()
        m.recalculate_mobile_apps_for_device = AsyncMock()
        return m

    async def test_list_devices(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = DeviceService(repo, reconciliation_service)
        items, total = await svc.list_devices()
        assert items == []
        assert total == 0
        repo.list.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_list_devices_paginated(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = DeviceService(repo, reconciliation_service)
        await svc.list_devices(skip=10, limit=20)
        repo.list.assert_called_once_with(skip=10, limit=20)

    async def test_get_device_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = DeviceService(repo, reconciliation_service)
        result = await svc.get_device(1)
        assert result is fake
        repo.get_by_id.assert_called_once_with(1)

    async def test_get_device_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = DeviceService(repo, reconciliation_service)
        result = await svc.get_device(999)
        assert result is None

    async def test_update_device_triggers_reconciliation(
        self, repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = DeviceService(repo, reconciliation_service)
        data = DeviceUpdate(connection_status="Disconnected")
        result = await svc.update_device(1, data)
        assert result == 1
        repo.update.assert_called_once_with(1, data)
        reconciliation_service.recalculate_profiles_for_device.assert_awaited_once_with(1)
        reconciliation_service.recalculate_mobile_apps_for_device.assert_awaited_once_with(1)

    async def test_update_device_non_trigger_field_skips_reconciliation(
        self, repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = DeviceService(repo, reconciliation_service)
        data = DeviceUpdate(network={"wifi": {"ssid": "Guest"}})
        result = await svc.update_device(1, data)
        assert result == 1
        reconciliation_service.recalculate_profiles_for_device.assert_not_called()
        reconciliation_service.recalculate_mobile_apps_for_device.assert_not_called()

    async def test_update_device_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        repo.update = AsyncMock(return_value=0)
        svc = DeviceService(repo, reconciliation_service)
        result = await svc.update_device(999, DeviceUpdate(connection_status="Disconnected"))
        assert result == 0
        repo.update.assert_called_once()
        reconciliation_service.recalculate_profiles_for_device.assert_not_called()
