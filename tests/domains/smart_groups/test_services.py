from unittest.mock import AsyncMock, MagicMock
import pytest

from app.domains.devices.criteria import CriteriaType
from app.infra.criteria import Criteria
from app.domains.smart_groups.services import SmartGroupService
from app.domains.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate


class TestSmartGroupService:
    @pytest.fixture
    def repo(self) -> None:
        m = MagicMock()
        m.list = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock()
        m.db = AsyncMock()
        return m

    async def test_list_groups(self, repo: MagicMock) -> None:
        svc = SmartGroupService(repo)
        await svc.list_groups()
        repo.list.assert_called_once_with(skip=0, limit=100)

    async def test_get_group(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo)
        result = await svc.get_group(1)
        assert result is fake

    async def test_create_group(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo)
        result = await svc.create_group(
            SmartGroupCreate(
                name="G",
                criteria=[
                    Criteria(
                        field="os_version",
                        operator="is",
                        type=CriteriaType.STRING,
                        value="Android 14",
                    ),
                ],
            ),
            created_by=1,
        )
        assert result is fake

    async def test_update_group(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo)
        result = await svc.update_group(1, SmartGroupUpdate(name="G2"))
        assert result is fake

    async def test_delete_group(self, repo: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=True)
        svc = SmartGroupService(repo)
        assert await svc.delete_group(1) is True
