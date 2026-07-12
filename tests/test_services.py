from unittest.mock import AsyncMock, MagicMock
import pytest
from app.devices.services import DeviceService
from app.smart_groups.services import SmartGroupService
from app.profiles.services import ProfileService
from app.users.services import UserService
from app.extension_attributes.services import ExtensionAttributeService
from app.inventory_search.services import InventorySearchService
from app.static_groups.services import StaticGroupService


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


class TestUserService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        return m

    async def test_list_users(self, repo):
        svc = UserService(repo)
        result = await svc.list_users()
        assert result == []
        repo.list_all.assert_called_once_with(skip=0, limit=100)

    async def test_list_users_paginated(self, repo):
        svc = UserService(repo)
        await svc.list_users(skip=10, limit=20)
        repo.list_all.assert_called_once_with(skip=10, limit=20)

    async def test_get_user_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.get_user(1)
        assert result is fake

    async def test_get_user_not_found(self, repo):
        svc = UserService(repo)
        result = await svc.get_user(999)
        assert result is None

    async def test_create_user(self, repo):
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.create_user({"email": "a@b.com", "name": "test", "password": "secret123"})
        assert result is fake
        create_args = repo.create.call_args[0][0]
        assert create_args["email"] == "a@b.com"
        assert "password" not in create_args
        assert "password_hash" in create_args

    async def test_update_user_with_password(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.update_user(1, {"password": "newpass"})
        assert result is fake
        update_args = repo.update.call_args[0][1]
        assert "password" not in update_args
        assert "password_hash" in update_args

    async def test_update_user_without_password(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.update_user(1, {"name": "new name"})
        assert result is fake
        repo.update.assert_called_once_with(1, {"name": "new name"})

    async def test_update_user_empty_data(self, repo):
        svc = UserService(repo)
        result = await svc.update_user(1, {})
        assert result is None
        repo.update.assert_not_called()

    async def test_delete_user(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = UserService(repo)
        assert await svc.delete_user(1) is True
        repo.delete.assert_called_once_with(1)

    async def test_delete_user_not_found(self, repo):
        repo.delete = AsyncMock(return_value=False)
        svc = UserService(repo)
        assert await svc.delete_user(999) is False


class TestExtensionAttributeService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock(return_value=0)
        return m

    async def test_list_attributes(self, repo):
        svc = ExtensionAttributeService(repo)
        items, total = await svc.list_attributes()
        assert items == []
        assert total == 0
        repo.list_all.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_list_attributes_paginated(self, repo):
        svc = ExtensionAttributeService(repo)
        await svc.list_attributes(skip=5, limit=15)
        repo.list_all.assert_called_once_with(skip=5, limit=15)

    async def test_get_attribute_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = ExtensionAttributeService(repo)
        result = await svc.get_attribute(1)
        assert result is fake

    async def test_get_attribute_not_found(self, repo):
        svc = ExtensionAttributeService(repo)
        result = await svc.get_attribute(999)
        assert result is None

    async def test_create_attribute(self, repo):
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = ExtensionAttributeService(repo)
        result = await svc.create_attribute({"name": "ext1"})
        assert result is fake
        repo.create.assert_called_once_with({"name": "ext1"})

    async def test_update_attribute(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = ExtensionAttributeService(repo)
        result = await svc.update_attribute(1, {"name": "ext2"})
        assert result is fake

    async def test_delete_attribute(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = ExtensionAttributeService(repo)
        assert await svc.delete_attribute(1) is True

    async def test_delete_attribute_not_found(self, repo):
        repo.delete = AsyncMock(return_value=False)
        svc = ExtensionAttributeService(repo)
        assert await svc.delete_attribute(999) is False


class TestInventorySearchService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock(return_value=0)
        return m

    async def test_list_searches(self, repo):
        svc = InventorySearchService(repo)
        items, total = await svc.list_searches()
        assert items == []
        assert total == 0

    async def test_list_searches_paginated(self, repo):
        svc = InventorySearchService(repo)
        await svc.list_searches(skip=5, limit=15)
        repo.list_all.assert_called_once_with(skip=5, limit=15)

    async def test_get_search_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = InventorySearchService(repo)
        result = await svc.get_search(1)
        assert result is fake

    async def test_get_search_not_found(self, repo):
        svc = InventorySearchService(repo)
        result = await svc.get_search(999)
        assert result is None

    async def test_create_search(self, repo):
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = InventorySearchService(repo)
        result = await svc.create_search({"name": "s1"})
        assert result is fake

    async def test_update_search(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = InventorySearchService(repo)
        result = await svc.update_search(1, {"name": "s2"})
        assert result is fake

    async def test_delete_search(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = InventorySearchService(repo)
        assert await svc.delete_search(1) is True

    async def test_delete_search_not_found(self, repo):
        repo.delete = AsyncMock(return_value=False)
        svc = InventorySearchService(repo)
        assert await svc.delete_search(999) is False


class TestStaticGroupService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock(return_value=0)
        m.get_device_serial_numbers = AsyncMock(return_value=[])
        m.set_device_serial_numbers = AsyncMock()
        m.db = AsyncMock()
        return m

    async def test_list_groups(self, repo):
        svc = StaticGroupService(repo)
        result = await svc.list_groups()
        assert result == []
        repo.list_all.assert_called_once_with(skip=0, limit=100)

    async def test_list_groups_paginated(self, repo):
        svc = StaticGroupService(repo)
        await svc.list_groups(skip=5, limit=15)
        repo.list_all.assert_called_once_with(skip=5, limit=15)

    async def test_get_group_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = StaticGroupService(repo)
        result = await svc.get_group(1)
        assert result is fake

    async def test_get_group_not_found(self, repo):
        svc = StaticGroupService(repo)
        result = await svc.get_group(999)
        assert result is None

    async def test_create_group(self, repo):
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = StaticGroupService(repo)
        result = await svc.create_group({"name": "G"})
        assert result is fake

    async def test_update_group(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = StaticGroupService(repo)
        result = await svc.update_group(1, {"name": "G2"})
        assert result is fake

    async def test_delete_group(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = StaticGroupService(repo)
        assert await svc.delete_group(1) is True

    async def test_get_device_serial_numbers(self, repo):
        repo.get_device_serial_numbers = AsyncMock(return_value=["SN001", "SN002"])
        svc = StaticGroupService(repo)
        result = await svc.get_device_serial_numbers(1)
        assert result == ["SN001", "SN002"]

    async def test_set_device_serial_numbers(self, repo):
        svc = StaticGroupService(repo)
        await svc.set_device_serial_numbers(1, ["SN001", "SN002"])
        repo.set_device_serial_numbers.assert_called_once_with(1, ["SN001", "SN002"])


class TestProfileServiceRecalculate:
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

    async def test_recalculate_profile_not_found(self, repo):
        repo.get_by_id = AsyncMock(return_value=None)
        svc = ProfileService(repo)
        await svc._recalculate_assignments(999)
        repo.delete_non_direct_assignments.assert_not_called()

    async def test_recalculate_empty_scope(self, repo):
        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)
        repo.get_scope = AsyncMock(return_value=[])
        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)
        repo.delete_non_direct_assignments.assert_awaited_once_with(1)

    async def test_recalculate_all_devices_scope(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        scope_entry = MagicMock(spec=ProfileScope)
        scope_entry.target_type = "ALL_DEVICES"
        scope_entry.target_id = None
        repo.get_scope = AsyncMock(return_value=[scope_entry])

        device1 = MagicMock()
        device1.id = 10
        device2 = MagicMock()
        device2.id = 20

        mock_result = MagicMock()
        mock_result.all.return_value = [(10,), (20,)]
        repo.db.execute = AsyncMock(return_value=mock_result)

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        assert repo.upsert_assignment.await_count == 2

    async def test_recalculate_device_scope(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        scope_entry = MagicMock(spec=ProfileScope)
        scope_entry.target_type = "DEVICE"
        scope_entry.target_id = 42
        repo.get_scope = AsyncMock(return_value=[scope_entry])

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        repo.upsert_assignment.assert_awaited_once()
        call_kwargs = repo.upsert_assignment.call_args[0][0]
        assert call_kwargs["device_id"] == 42
        assert call_kwargs["source"] == "DIRECT"

    async def test_recalculate_static_group_scope(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        scope_entry = MagicMock(spec=ProfileScope)
        scope_entry.target_type = "STATIC_GROUP"
        scope_entry.target_id = 5
        repo.get_scope = AsyncMock(return_value=[scope_entry])

        sg_dev_result = MagicMock()
        sg_dev_result.all.return_value = [(10,)]

        repo.db.execute = AsyncMock(return_value=sg_dev_result)

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        repo.upsert_assignment.assert_awaited_once()
        call_kwargs = repo.upsert_assignment.call_args[0][0]
        assert call_kwargs["source"] == "STATIC_GROUP"
        assert call_kwargs["source_id"] == 5

    async def test_recalculate_static_group_empty_serials(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        scope_entry = MagicMock(spec=ProfileScope)
        scope_entry.target_type = "STATIC_GROUP"
        scope_entry.target_id = 5
        repo.get_scope = AsyncMock(return_value=[scope_entry])

        serial_result = MagicMock()
        serial_result.all.return_value = []
        repo.db.execute = AsyncMock(return_value=serial_result)

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        repo.upsert_assignment.assert_not_called()

    async def test_recalculate_smart_group_scope_no_criteria(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        scope_entry = MagicMock(spec=ProfileScope)
        scope_entry.target_type = "SMART_GROUP"
        scope_entry.target_id = 3
        repo.get_scope = AsyncMock(return_value=[scope_entry])

        smart_group = MagicMock()
        smart_group.criteria = None
        sg_result = MagicMock()
        sg_result.scalar_one_or_none.return_value = smart_group
        repo.db.execute = AsyncMock(return_value=sg_result)

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        repo.upsert_assignment.assert_not_called()

    async def test_recalculate_smart_group_scope_with_criteria(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        scope_entry = MagicMock(spec=ProfileScope)
        scope_entry.target_type = "SMART_GROUP"
        scope_entry.target_id = 3
        repo.get_scope = AsyncMock(return_value=[scope_entry])

        smart_group = MagicMock()
        smart_group.criteria = [{"criteria": "connection_status", "operator": "is", "value": "Online"}]
        sg_result = MagicMock()
        sg_result.scalar_one_or_none.return_value = smart_group

        dev_result = MagicMock()
        dev_result.all.return_value = [(10,), (20,)]

        repo.db.execute = AsyncMock(side_effect=[sg_result, dev_result])

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        assert repo.upsert_assignment.await_count == 2
        call_kwargs = repo.upsert_assignment.call_args[0][0]
        assert call_kwargs["source"] == "SMART_GROUP"
        assert call_kwargs["source_id"] == 3

    async def test_recalculate_smart_group_nonexistent_group(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        scope_entry = MagicMock(spec=ProfileScope)
        scope_entry.target_type = "SMART_GROUP"
        scope_entry.target_id = 999
        repo.get_scope = AsyncMock(return_value=[scope_entry])

        sg_result = MagicMock()
        sg_result.scalar_one_or_none.return_value = None
        repo.db.execute = AsyncMock(return_value=sg_result)

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        repo.upsert_assignment.assert_not_called()

    async def test_recalculate_smart_group_empty_criteria_list(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        scope_entry = MagicMock(spec=ProfileScope)
        scope_entry.target_type = "SMART_GROUP"
        scope_entry.target_id = 3
        repo.get_scope = AsyncMock(return_value=[scope_entry])

        smart_group = MagicMock()
        smart_group.criteria = []
        sg_result = MagicMock()
        sg_result.scalar_one_or_none.return_value = smart_group
        repo.db.execute = AsyncMock(return_value=sg_result)

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        repo.upsert_assignment.assert_not_called()

    async def test_recalculate_mixed_scopes(self, repo):
        from app.profiles.profile_scope import ProfileScope

        profile = MagicMock()
        profile.version = 1
        repo.get_by_id = AsyncMock(return_value=profile)

        device_scope = MagicMock(spec=ProfileScope)
        device_scope.target_type = "DEVICE"
        device_scope.target_id = 42

        all_scope = MagicMock(spec=ProfileScope)
        all_scope.target_type = "ALL_DEVICES"
        all_scope.target_id = None

        repo.get_scope = AsyncMock(return_value=[device_scope, all_scope])

        all_devices_result = MagicMock()
        all_devices_result.all.return_value = [(10,)]

        repo.db.execute = AsyncMock(return_value=all_devices_result)

        svc = ProfileService(repo)
        await svc._recalculate_assignments(1)

        repo.delete_non_direct_assignments.assert_awaited_once_with(1)
        assert repo.upsert_assignment.await_count == 2
