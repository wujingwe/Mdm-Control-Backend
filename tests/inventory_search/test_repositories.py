from app.common.enums import CriteriaType
from app.criteria import Criteria
from app.inventory_search.repositories import InventorySearchRepository
from app.inventory_search.schemas import InventorySearchCreate, InventorySearchUpdate
from sqlalchemy.ext.asyncio import AsyncSession

_CRITERIA = [
    Criteria(
        field="connection_status",
        operator="is",
        type=CriteriaType.STRING,
        value="Connected",
    ),
]


class TestInventorySearchRepository:
    async def test_create(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="search1", criteria=_CRITERIA, created_by=1))
        assert created.id is not None
        assert created.name == "search1"

    async def test_list(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        await repo.create(InventorySearchCreate(name="s1", criteria=_CRITERIA, created_by=1))
        await repo.create(InventorySearchCreate(name="s2", criteria=_CRITERIA, created_by=1))
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        for i in range(5):
            await repo.create(InventorySearchCreate(name=f"s{i}", criteria=_CRITERIA, created_by=1))
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", criteria=_CRITERIA, created_by=1))
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "s1"

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", criteria=_CRITERIA, created_by=1))
        updated = await repo.update(created.id, InventorySearchUpdate(name="s2"))
        assert updated is not None
        assert updated.name == "s2"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        assert await repo.update(999, InventorySearchUpdate(name="x")) is None

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", criteria=_CRITERIA, created_by=1))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        assert await repo.delete(999) is True

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        assert await repo.count() == 0
        await repo.create(InventorySearchCreate(name="s1", criteria=_CRITERIA, created_by=1))
        assert await repo.count() == 1

    async def test_create_with_criteria(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        created = await repo.create(
            InventorySearchCreate(
                name="Online Android",
                created_by=1,
                criteria=[
                    Criteria(
                        field="connection_status",
                        operator="is",
                        type=CriteriaType.STRING,
                        value="Connected",
                    ),
                    Criteria(
                        field="os_version",
                        operator="is",
                        type=CriteriaType.STRING,
                        value="Android 14",
                    ),
                ],
            )
        )
        assert created.id is not None
        found = await repo.get_by_id(created.id)
        assert found.criteria is not None
        assert len(found.criteria) == 2
        assert found.criteria[0]["field"] == "connection_status"
        assert found.criteria[1]["field"] == "os_version"

    async def test_update_criteria(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        created = await repo.create(
            InventorySearchCreate(
                name="Test Search",
                created_by=1,
                criteria=[
                    Criteria(
                        field="os_version",
                        operator="is",
                        type=CriteriaType.STRING,
                        value="Android 14",
                    ),
                ],
            )
        )
        updated = await repo.update(
            created.id,
            InventorySearchUpdate(
                criteria=[
                    Criteria(
                        field="battery_status",
                        operator="lessThan",
                        type=CriteriaType.NUMBER,
                        value="15",
                    ),
                ],
            ),
        )
        assert updated.criteria is not None
        assert len(updated.criteria) == 1
        assert updated.criteria[0]["field"] == "battery_status"

    async def test_update_criteria_empty_list_rejected(self, db_session: AsyncSession) -> None:
        from pydantic import ValidationError
        import pytest

        with pytest.raises(ValidationError):
            InventorySearchUpdate(criteria=[])

    async def test_update_name_preserves_criteria(self, db_session: AsyncSession) -> None:
        repo = InventorySearchRepository(db_session)
        created = await repo.create(
            InventorySearchCreate(
                name="Original Name",
                created_by=1,
                criteria=[
                    Criteria(
                        field="os_version",
                        operator="is",
                        type=CriteriaType.STRING,
                        value="Android 14",
                    ),
                ],
            )
        )
        updated = await repo.update(created.id, InventorySearchUpdate(name="New Name"))
        assert updated.name == "New Name"
        found = await repo.get_by_id(created.id)
        assert len(found.criteria) == 1
        assert found.criteria[0]["field"] == "os_version"
