from unittest.mock import AsyncMock, MagicMock
import pytest
from app.static_groups.services import StaticGroupService
from app.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate


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
        m.db = AsyncMock()
        return m

    async def test_list_groups(self, repo):
        svc = StaticGroupService(repo)
        result = await svc.list_groups()
        assert result == ([], 0)
        repo.list_all.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_awaited_once()

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
        data = StaticGroupCreate(
            name="G", created_by=1, device_serial_numbers=["SN001"]
        )
        result = await svc.create_group(data)
        assert result is fake
        repo.create.assert_called_once_with(data)

    async def test_update_group(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = StaticGroupService(repo)
        result = await svc.update_group(1, StaticGroupUpdate(name="G2"))
        assert result is fake

    async def test_delete_group(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = StaticGroupService(repo)
        assert await svc.delete_group(1) is True
