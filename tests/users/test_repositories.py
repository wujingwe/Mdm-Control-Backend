from app.users.repositories import UserRepository
from app.users.schemas import UserCreate, UserUpdate
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserRepository:
    async def test_crud(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        created = await repo.create(
            UserCreate(
                email="j@example.com",
                name="jdoe",
                permissions=frozenset({"admin"}),
            )
        )
        assert created.id is not None
        assert created.name == "jdoe"

        found = await repo.get_by_id(created.id)
        assert found.email == "j@example.com"

        assert await repo.delete(created.id) is True

    async def test_list(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        base = dict(permissions=frozenset({"viewer"}))
        await repo.create(UserCreate(email="u1@e.com", name="u1", **base))
        await repo.create(UserCreate(email="u2@e.com", name="u2", **base))
        assert len(await repo.list()) == 2

    async def test_update(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        created = await repo.create(
            UserCreate(
                email="upd@example.com",
                name="orig",
                permissions=frozenset({"viewer"}),
            )
        )
        updated = await repo.update(created.id, UserUpdate(name="updated"))
        assert updated is not None
        assert updated.name == "updated"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        assert await repo.update(999, UserUpdate(name="x")) is None

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        assert await repo.count() == 0
        await repo.create(
            UserCreate(
                email="c@e.com",
                name="c",
                permissions=frozenset({"viewer"}),
            )
        )
        assert await repo.count() == 1

    async def test_list_pagination(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        base = dict(permissions=frozenset({"viewer"}))
        for i in range(5):
            await repo.create(UserCreate(email=f"u{i}@e.com", name=f"u{i}", **base))
        items = await repo.list(skip=2, limit=2)
        assert len(items) == 2

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        assert await repo.delete(999) is True
