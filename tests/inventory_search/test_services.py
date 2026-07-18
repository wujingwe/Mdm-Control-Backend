from unittest.mock import AsyncMock, MagicMock
import pytest
from app.inventory_search.services import InventorySearchService
from app.inventory_search.schemas import InventorySearchCreate, InventorySearchUpdate


class TestInventorySearchService:
    @pytest.fixture
    def repo(self) -> None:
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock(return_value=0)
        return m

    async def test_list_searches(self, repo: MagicMock) -> None:
        svc = InventorySearchService(repo)
        items, total = await svc.list_searches()
        assert items == []
        assert total == 0

    async def test_list_searches_paginated(self, repo: MagicMock) -> None:
        svc = InventorySearchService(repo)
        await svc.list_searches(skip=5, limit=15)
        repo.list_all.assert_called_once_with(skip=5, limit=15)

    async def test_get_search_found(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = InventorySearchService(repo)
        result = await svc.get_search(1)
        assert result is fake

    async def test_get_search_not_found(self, repo: MagicMock) -> None:
        svc = InventorySearchService(repo)
        result = await svc.get_search(999)
        assert result is None

    async def test_create_search(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = InventorySearchService(repo)
        result = await svc.create_search(
            InventorySearchCreate(
                name="s1",
                criteria=[
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                    }
                ],
                created_by=1,
            )
        )
        assert result is fake

    async def test_update_search(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = InventorySearchService(repo)
        result = await svc.update_search(1, InventorySearchUpdate(name="s2"))
        assert result is fake

    async def test_delete_search(self, repo: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=True)
        svc = InventorySearchService(repo)
        assert await svc.delete_search(1) is True

    async def test_delete_search_not_found(self, repo: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=False)
        svc = InventorySearchService(repo)
        assert await svc.delete_search(999) is False
