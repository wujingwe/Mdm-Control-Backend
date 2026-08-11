from typing import cast

from app.domains.users.enums import Permission
from app.domains.users.repositories import UserRepository
from app.domains.users.schemas import UserCreate, UserUpdate
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserRepository:
    async def test_crud(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        created = await repo.create(
            UserCreate(
                email="j@example.com",
                name="jdoe",
                permissions=cast(frozenset[Permission], frozenset({"admin"})),
            )
        )
        assert created.id is not None
        assert created.name == "jdoe"

        found = await repo.get_by_id(created.id)
        assert found.email == "j@example.com"

        assert await repo.delete(created.id) == 1

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
                permissions=cast(frozenset[Permission], frozenset({"viewer"})),
            )
        )
        assert await repo.update(created.id, UserUpdate(name="updated")) == 1
        found = await repo.get_by_id(created.id)
        assert found.name == "updated"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        assert await repo.update(999, UserUpdate(name="x")) == 0

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        assert await repo.count() == 0
        await repo.create(
            UserCreate(
                email="c@e.com",
                name="c",
                permissions=cast(frozenset[Permission], frozenset({"viewer"})),
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
        assert await repo.delete(999) == 0
