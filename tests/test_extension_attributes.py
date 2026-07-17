import pytest
from app.extension_attributes.repositories import ExtensionAttributeRepository
from app.extension_attributes.schemas import (
    ExtensionAttributeCreate,
    ExtensionAttributeUpdate,
)
from app.common.enums import ExtensionDataType, ExtensionInputType


class TestExtensionAttributeRepository:
    async def test_crud(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(
            ExtensionAttributeCreate(
                name="Department",
                description="Device department",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.POPUP_MENU,
                popup_choices=["Engineering", "Sales"],
                created_by=1,
            )
        )
        assert created.id is not None
        assert created.name == "Department"
        assert created.data_type == ExtensionDataType.STRING
        assert created.input_type == ExtensionInputType.POPUP_MENU
        assert created.popup_choices == ["Engineering", "Sales"]

        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "Department"

        updated = await repo.update(
            created.id, ExtensionAttributeUpdate(description="Updated desc")
        )
        assert updated.description == "Updated desc"

        assert await repo.count() == 1

    async def test_unique_name(self, db_session):
        from app.core.exceptions import ConflictError

        repo = ExtensionAttributeRepository(db_session)
        await repo.create(
            ExtensionAttributeCreate(
                name="Dept",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
                created_by=1,
            )
        )
        with pytest.raises(ConflictError):
            await repo.create(
                ExtensionAttributeCreate(
                    name="Dept",
                    data_type=ExtensionDataType.INTEGER,
                    input_type=ExtensionInputType.TEXT_FIELD,
                    created_by=1,
                )
            )

    async def test_list(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        await repo.create(
            ExtensionAttributeCreate(
                name="A",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
                created_by=1,
            )
        )
        await repo.create(
            ExtensionAttributeCreate(
                name="B",
                data_type=ExtensionDataType.INTEGER,
                input_type=ExtensionInputType.TEXT_FIELD,
                created_by=1,
            )
        )
        items = await repo.list_all()
        assert len(items) == 2

    async def test_delete(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(
            ExtensionAttributeCreate(
                name="X",
                data_type=ExtensionDataType.STRING,
                input_type=ExtensionInputType.TEXT_FIELD,
                created_by=1,
            )
        )
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.delete(999) is False
