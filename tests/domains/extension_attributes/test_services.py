from unittest.mock import AsyncMock, MagicMock
import pytest

from app.domains.extension_attributes.enums import ExtensionInputType, ExtensionDataType
from app.domains.extension_attributes.services import ExtensionAttributeService
from app.domains.extension_attributes.schemas import (
    ExtensionAttributeCreate,
    ExtensionAttributeUpdate,
)


class TestExtensionAttributeService:
    @pytest.fixture
    def repo(self) -> None:
        m = MagicMock()
        m.list = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock(return_value=0)
        return m

    async def test_list_attributes(self, repo: MagicMock) -> None:
        svc = ExtensionAttributeService(repo)
        items, total = await svc.list_attributes()
        assert items == []
        assert total == 0
        repo.list.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_list_attributes_paginated(self, repo: MagicMock) -> None:
        svc = ExtensionAttributeService(repo)
        await svc.list_attributes(skip=5, limit=15)
        repo.list.assert_called_once_with(skip=5, limit=15)

    async def test_get_attribute_found(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = ExtensionAttributeService(repo)
        result = await svc.get_attribute(1)
        assert result is fake

    async def test_get_attribute_not_found(self, repo: MagicMock) -> None:
        svc = ExtensionAttributeService(repo)
        result = await svc.get_attribute(999)
        assert result is None

    async def test_create_attribute(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = ExtensionAttributeService(repo)
        result = await svc.create_attribute(
            ExtensionAttributeCreate(
                name="ext1", data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD
            ),
            created_by=1,
        )
        assert result is fake

    async def test_update_attribute(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = ExtensionAttributeService(repo)
        result = await svc.update_attribute(1, ExtensionAttributeUpdate(name="ext2"))
        assert result is fake

    async def test_delete_attribute(self, repo: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=True)
        svc = ExtensionAttributeService(repo)
        assert await svc.delete_attribute(1) is True

    async def test_delete_attribute_not_found(self, repo: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=False)
        svc = ExtensionAttributeService(repo)
        assert await svc.delete_attribute(999) is False
