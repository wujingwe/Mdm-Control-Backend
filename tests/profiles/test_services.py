from unittest.mock import AsyncMock, MagicMock
import pytest
from app.profiles.services import ProfileService
from app.profiles.schemas import ProfileCreate, ProfileUpdate


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
        return m

    async def test_list_profiles(self, repo):
        svc = ProfileService(repo)
        items, total = await svc.list_profiles()
        assert items == []
        assert total == 0

    async def test_list_profiles_paginated(self, repo):
        svc = ProfileService(repo)
        await svc.list_profiles(skip=5, limit=15)
        repo.list_all.assert_called_once_with(skip=5, limit=15)

    async def test_get_profile_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = ProfileService(repo)
        result = await svc.get_profile(1)
        assert result is fake

    async def test_get_profile_not_found(self, repo):
        svc = ProfileService(repo)
        result = await svc.get_profile(999)
        assert result is None

    async def test_create_profile(self, repo):
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = ProfileService(repo)
        result = await svc.create_profile(ProfileCreate(name="P", created_by=1))
        assert result is fake

    async def test_update_profile(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = ProfileService(repo)
        result = await svc.update_profile(1, ProfileUpdate(name="P2"))
        assert result is fake

    async def test_delete_profile(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = ProfileService(repo)
        assert await svc.delete_profile(1) is True

    async def test_delete_profile_not_found(self, repo):
        repo.delete = AsyncMock(return_value=False)
        svc = ProfileService(repo)
        assert await svc.delete_profile(999) is False

    async def test_get_scope(self, repo):
        svc = ProfileService(repo)
        result = await svc.get_scope(1)
        assert result == []
        repo.get_scope.assert_called_once_with(1)

    async def test_set_scope(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = ProfileService(repo)
        await svc.set_scope(1, [])
        repo.set_scope.assert_called_once_with(1, [])

    async def test_get_assignments(self, repo):
        svc = ProfileService(repo)
        result = await svc.get_assignments(1)
        assert result == []
        repo.get_assignments.assert_called_once_with(1)

    async def test_update_assignment_status_not_found(self, repo):
        svc = ProfileService(repo)
        result = await svc.update_assignment_status(1, 100, "Applied")
        assert result is None
