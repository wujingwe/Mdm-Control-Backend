import pytest
from app.infra.core.exceptions import ConflictError
from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
from app.domains.extension_attributes.schemas import (
    ExtensionAttributeCreate,
    ExtensionAttributeUpdate,
)
from app.infra.common.enums import ExtensionDataType, ExtensionInputType
from sqlalchemy.ext.asyncio import AsyncSession


class TestExtensionAttributeRepository:
    async def test_create(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(
            ExtensionAttributeCreate(
                name="ext1",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
            ),
            created_by=1,
        )
        assert created.id is not None
        assert created.name == "ext1"

    async def test_create_unique_name(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        data = ExtensionAttributeCreate(
            name="ext1",
            data_type=ExtensionDataType.STRING,
            input_type=ExtensionInputType.TEXT_FIELD,
        )
        await repo.create(data, created_by=1)
        with pytest.raises(ConflictError):
            await repo.create(data, created_by=1)

    async def test_list(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        base = dict(
            data_type=ExtensionDataType.STRING,
            input_type=ExtensionInputType.TEXT_FIELD,
        )
        await repo.create(ExtensionAttributeCreate(name="ext1", **base), created_by=1)
        await repo.create(ExtensionAttributeCreate(name="ext2", **base), created_by=1)
        items = await repo.list()
        assert len(items) == 2

    async def test_list_pagination(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        base = dict(
            data_type=ExtensionDataType.STRING,
            input_type=ExtensionInputType.TEXT_FIELD,
        )
        for i in range(5):
            await repo.create(ExtensionAttributeCreate(name=f"ext{i}", **base), created_by=1)
        items = await repo.list(skip=1, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(
            ExtensionAttributeCreate(
                name="ext1",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
            ),
            created_by=1,
        )
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "ext1"

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(
            ExtensionAttributeCreate(
                name="ext1",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
            ),
            created_by=1,
        )
        updated = await repo.update(created.id, ExtensionAttributeUpdate(name="ext2"))
        assert updated is not None
        assert updated.name == "ext2"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.update(999, ExtensionAttributeUpdate(name="x")) is None

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(
            ExtensionAttributeCreate(
                name="ext1",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
            ),
            created_by=1,
        )
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.count() == 0
        await repo.create(
            ExtensionAttributeCreate(
                name="ext1",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
            ),
            created_by=1,
        )
        assert await repo.count() == 1
