from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.device import DeviceService
from app.services.smart_group import SmartGroupService
from app.services.policy import PolicyService
from app.services.profile import ProfileService


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


class TestProfileService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock(return_value=0)
        m.get_scope = AsyncMock(return_value=[])
        m.set_scope = AsyncMock()
        m.get_assignments = AsyncMock(return_value=[])
        m.get_assignment = AsyncMock(return_value=None)
        m.upsert_assignment = AsyncMock()
        m.delete_non_direct_assignments = AsyncMock()
        m.db = AsyncMock()
        return m

    async def test_list_profiles(self, repo):
        svc = ProfileService(repo)
        items, total = await svc.list_profiles()
        assert items == []
        assert total == 0
        repo.list_all.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_list_profiles_paginated(self, repo):
        svc = ProfileService(repo)
        await svc.list_profiles(skip=10, limit=20)
        repo.list_all.assert_called_once_with(skip=10, limit=20)

    async def test_get_profile_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = ProfileService(repo)
        result = await svc.get_profile(1)
        assert result is fake
        repo.get_by_id.assert_called_once_with(1)

    async def test_get_profile_not_found(self, repo):
        svc = ProfileService(repo)
        result = await svc.get_profile(999)
        assert result is None

    async def test_create_profile(self, repo):
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = ProfileService(repo)
        result = await svc.create_profile({"name": "P"})
        assert result is fake
        repo.create.assert_called_once_with({"name": "P"})

    async def test_update_profile(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = ProfileService(repo)
        result = await svc.update_profile(1, {"name": "P2"})
        assert result is fake
        repo.update.assert_called_once_with(1, {"name": "P2"})

    async def test_delete_profile(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = ProfileService(repo)
        assert await svc.delete_profile(1) is True
        repo.delete.assert_called_once_with(1)

    async def test_get_scope(self, repo):
        fake_scope = [MagicMock()]
        repo.get_scope = AsyncMock(return_value=fake_scope)
        svc = ProfileService(repo)
        result = await svc.get_scope(1)
        assert result == fake_scope
        repo.get_scope.assert_called_once_with(1)

    async def test_set_scope_triggers_recalculation(self, repo):
        repo.get_by_id = AsyncMock(return_value=MagicMock(version=1))
        repo.get_scope = AsyncMock(return_value=[])
        svc = ProfileService(repo)
        await svc.set_scope(1, [{"target_type": "ALL_DEVICES"}])
        repo.set_scope.assert_called_once_with(1, [{"target_type": "ALL_DEVICES"}])
        repo.delete_non_direct_assignments.assert_awaited_once_with(1)

    async def test_get_assignments(self, repo):
        fake_assignments = [MagicMock()]
        repo.get_assignments = AsyncMock(return_value=fake_assignments)
        svc = ProfileService(repo)
        result = await svc.get_assignments(1)
        assert result == fake_assignments

    async def test_update_assignment_status_found(self, repo):
        from datetime import datetime, timezone
        assignment = MagicMock(
            profile_id=1, device_id=10, source="DIRECT",
            source_id=None, profile_version=1,
        )
        repo.get_assignment = AsyncMock(return_value=assignment)
        updated = MagicMock()
        repo.upsert_assignment = AsyncMock(return_value=updated)
        svc = ProfileService(repo)
        result = await svc.update_assignment_status(1, 10, "APPLIED")
        assert result is updated
        call_kwargs = repo.upsert_assignment.call_args[0][0]
        assert call_kwargs["status"] == "APPLIED"
        assert call_kwargs["applied_at"] is not None

    async def test_update_assignment_status_revoked(self, repo):
        assignment = MagicMock(
            profile_id=1, device_id=10, source="SMART_GROUP",
            source_id=5, profile_version=1,
        )
        repo.get_assignment = AsyncMock(return_value=assignment)
        updated = MagicMock()
        repo.upsert_assignment = AsyncMock(return_value=updated)
        svc = ProfileService(repo)
        result = await svc.update_assignment_status(1, 10, "REVOKED")
        assert result is updated
        call_kwargs = repo.upsert_assignment.call_args[0][0]
        assert call_kwargs["status"] == "REVOKED"
        assert call_kwargs["revoked_at"] is not None

    async def test_update_assignment_status_not_found(self, repo):
        repo.get_assignment = AsyncMock(return_value=None)
        svc = ProfileService(repo)
        result = await svc.update_assignment_status(1, 999, "APPLIED")
        assert result is None
