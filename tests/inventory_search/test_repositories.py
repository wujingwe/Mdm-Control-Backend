from app.inventory_search.repositories import InventorySearchRepository
from app.inventory_search.schemas import InventorySearchCreate, InventorySearchUpdate


class TestInventorySearchRepository:
    async def test_create(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="search1", created_by=1))
        assert created.id is not None
        assert created.name == "search1"

    async def test_list(self, db_session):
        repo = InventorySearchRepository(db_session)
        await repo.create(InventorySearchCreate(name="s1", created_by=1))
        await repo.create(InventorySearchCreate(name="s2", created_by=1))
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session):
        repo = InventorySearchRepository(db_session)
        for i in range(5):
            await repo.create(InventorySearchCreate(name=f"s{i}", created_by=1))
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", created_by=1))
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "s1"

    async def test_get_by_id_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", created_by=1))
        updated = await repo.update(created.id, InventorySearchUpdate(name="s2"))
        assert updated is not None
        assert updated.name == "s2"

    async def test_update_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.update(999, InventorySearchUpdate(name="x")) is None

    async def test_delete(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", created_by=1))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.count() == 0
        await repo.create(InventorySearchCreate(name="s1", created_by=1))
        assert await repo.count() == 1
