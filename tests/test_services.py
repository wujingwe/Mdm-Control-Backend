from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.device import DeviceService
from app.services.smart_group import SmartGroupService
from app.services.policy import PolicyService


class TestDeviceService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        m.get_by_ids = AsyncMock(return_value=[])
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

    async def test_assign_policy(self, repo):
        policy = MagicMock()
        device = MagicMock()
        device.id = 1
        device.policies = []
        repo.db.get = AsyncMock(return_value=policy)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = device
        repo.db.execute = AsyncMock(return_value=mock_result)

        svc = DeviceService(repo)
        result = await svc.assign_policy(1, 10)
        assert result is not None
        assert policy in device.policies
        repo.db.commit.assert_awaited_once()

    async def test_assign_policy_device_not_found(self, repo):
        repo.db.get = AsyncMock(return_value=MagicMock())
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = DeviceService(repo)
        result = await svc.assign_policy(999, 1)
        assert result is None


class TestPolicyService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        return m

    async def test_list_policies(self, repo):
        svc = PolicyService(repo)
        items, total = await svc.list_policies()
        repo.list_all.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_get_policy(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = PolicyService(repo)
        result = await svc.get_policy(1)
        assert result is fake

    async def test_get_policy_not_found(self, repo):
        svc = PolicyService(repo)
        result = await svc.get_policy(999)
        assert result is None


class TestSmartGroupService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock()
        m.db = AsyncMock()
        return m

    async def test_assign_policy(self, repo):
        policy = MagicMock()
        group = MagicMock()
        group.id = 1
        group.policies = []
        repo.db.get = AsyncMock(return_value=policy)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = group
        repo.db.execute = AsyncMock(return_value=mock_result)

        svc = SmartGroupService(repo)
        result = await svc.assign_policy(1, 10)
        assert result is not None
        assert policy in group.policies
        repo.db.commit.assert_awaited_once()

    async def test_assign_policy_already_assigned(self, repo):
        policy = MagicMock()
        policy.id = 10
        group = MagicMock()
        group.id = 1
        group.policies = [policy]
        repo.db.get = AsyncMock(return_value=policy)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = group
        repo.db.execute = AsyncMock(return_value=mock_result)

        svc = SmartGroupService(repo)
        result = await svc.assign_policy(1, 10)
        assert result is not None
        assert len(group.policies) == 1
        repo.db.commit.assert_not_called()

    async def test_assign_policy_group_not_found(self, repo):
        repo.db.get = AsyncMock(return_value=MagicMock())
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = SmartGroupService(repo)
        result = await svc.assign_policy(999, 1)
        assert result is None

    async def test_assign_policy_policy_not_found(self, repo):
        repo.db.get = AsyncMock(return_value=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        repo.db.execute = AsyncMock(return_value=mock_result)
        svc = SmartGroupService(repo)
        result = await svc.assign_policy(1, 999)
        assert result is None

    async def test_list_groups(self, repo):
        svc = SmartGroupService(repo)
        await svc.list_groups()
        repo.list_all.assert_called_once_with(skip=0, limit=100)

    async def test_get_group(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo)
        result = await svc.get_group(1)
        assert result is fake

    async def test_create_group(self, repo):
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo)
        result = await svc.create_group({"name": "G"})
        assert result is fake

    async def test_update_group(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo)
        result = await svc.update_group(1, {"name": "G2"})
        assert result is fake

    async def test_delete_group(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = SmartGroupService(repo)
        assert await svc.delete_group(1) is True
