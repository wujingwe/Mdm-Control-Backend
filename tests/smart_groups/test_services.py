from unittest.mock import AsyncMock, MagicMock
import pytest
from app.smart_groups.services import SmartGroupService
from app.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate


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
        result = await svc.create_group(
            SmartGroupCreate(
                name="G",
                criteria=[{"field": "os_version", "operator": "is", "type": "string", "value": "Android 14"}],
                created_by=1,
            )
        )
        assert result is fake

    async def test_update_group(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo)
        result = await svc.update_group(1, SmartGroupUpdate(name="G2"))
        assert result is fake

    async def test_delete_group(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = SmartGroupService(repo)
        assert await svc.delete_group(1) is True
