from app.smart_groups.repositories import SmartGroupRepository
from app.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate


class TestSmartGroupRepository:
    async def test_crud(self, db_session):
        repo = SmartGroupRepository(db_session)
        created = await repo.create(SmartGroupCreate(name="Group A", created_by=1))
        assert created.id is not None

        found = await repo.get_by_id(created.id)
        assert found.name == "Group A"

        updated = await repo.update(created.id, SmartGroupUpdate(description="desc"))
        assert updated.description == "desc"

        assert await repo.count() == 1

    async def test_delete(self, db_session):
        repo = SmartGroupRepository(db_session)
        created = await repo.create(SmartGroupCreate(name="G", created_by=1))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = SmartGroupRepository(db_session)
        assert await repo.delete(999) is False

    async def test_get_by_id_not_found(self, db_session):
        repo = SmartGroupRepository(db_session)
        assert await repo.get_by_id(999) is None
