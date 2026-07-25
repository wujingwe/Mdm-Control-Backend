from app.common.enums import CriteriaType
from app.criteria import Criteria
from app.smart_groups.repositories import SmartGroupRepository
from app.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate
from sqlalchemy.ext.asyncio import AsyncSession

_CRITERIA = [
    Criteria(
        field="os_version",
        operator="is",
        type=CriteriaType.STRING,
        value="Android 14",
    ),
]


class TestSmartGroupRepository:
    async def test_crud(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        created = await repo.create(SmartGroupCreate(name="Group A", criteria=_CRITERIA), created_by=1)
        assert created.id is not None

        found = await repo.get_by_id(created.id)
        assert found.name == "Group A"

        updated = await repo.update(created.id, SmartGroupUpdate(description="desc"))
        assert updated.description == "desc"

        assert await repo.count() == 1

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        created = await repo.create(SmartGroupCreate(name="G", criteria=_CRITERIA), created_by=1)
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        assert await repo.delete(999) is True

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_create_with_criteria(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        created = await repo.create(
            SmartGroupCreate(
                name="Android Group",
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
        assert created.id is not None
        found = await repo.get_by_id(created.id)
        assert found.criteria is not None
        assert len(found.criteria) == 1
        assert found.criteria[0]["field"] == "os_version"

    async def test_create_with_multiple_criteria(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        created = await repo.create(
            SmartGroupCreate(
                name="Complex Group",
                criteria=[
                    Criteria(
                        field="os_version",
                        operator="is",
                        type=CriteriaType.STRING,
                        value="Android 14",
                    ),
                    Criteria(
                        field="battery_status",
                        operator="lessThan",
                        type=CriteriaType.NUMBER,
                        value="20",
                        left_parentheses=True,
                    ),
                ],
            ),
            created_by=1,
        )
        found = await repo.get_by_id(created.id)
        assert len(found.criteria) == 2
        assert found.criteria[0]["field"] == "os_version"
        assert found.criteria[1]["field"] == "battery_status"
        assert found.criteria[1]["left_parentheses"] is True

    async def test_update_criteria(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        created = await repo.create(
            SmartGroupCreate(
                name="Test Group",
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
        updated = await repo.update(
            created.id,
            SmartGroupUpdate(
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

    async def test_update_criteria_empty_list_accepted(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        created = await repo.create(
            SmartGroupCreate(
                name="Test Group",
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
        updated = await repo.update(created.id, SmartGroupUpdate(criteria=[]))
        assert updated.criteria == []

    async def test_update_name_preserves_criteria(self, db_session: AsyncSession) -> None:
        repo = SmartGroupRepository(db_session)
        created = await repo.create(
            SmartGroupCreate(
                name="Original Name",
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
        updated = await repo.update(created.id, SmartGroupUpdate(name="New Name"))
        assert updated.name == "New Name"
        found = await repo.get_by_id(created.id)
        assert len(found.criteria) == 1
        assert found.criteria[0]["field"] == "os_version"
