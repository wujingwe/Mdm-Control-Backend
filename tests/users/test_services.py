from unittest.mock import AsyncMock, MagicMock
import pytest
from app.users.services import UserService
from app.users.schemas import UserCreate


class TestUserService:
    @pytest.fixture
    def repo(self) -> None:
        m = MagicMock()
        m.list = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        return m

    async def test_list_users(self, repo: MagicMock) -> None:
        svc = UserService(repo)
        items, total = await svc.list_users()
        assert items == []
        assert total == 0
        repo.list.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_list_users_paginated(self, repo: MagicMock) -> None:
        svc = UserService(repo)
        await svc.list_users(skip=10, limit=20)
        repo.list.assert_called_once_with(skip=10, limit=20)

    async def test_get_user_found(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.get_user(1)
        assert result is fake

    async def test_get_user_not_found(self, repo: MagicMock) -> None:
        svc = UserService(repo)
        result = await svc.get_user(999)
        assert result is None

    async def test_create_user(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.create_user(UserCreate(email="a@b.com", name="test"))
        assert result is fake
        create_arg = repo.create.call_args[0][0]
        assert create_arg.email == "a@b.com"

    async def test_delete_user(self, repo: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=True)
        svc = UserService(repo)
        assert await svc.delete_user(1) is True
        repo.delete.assert_called_once_with(1)

    async def test_delete_user_not_found(self, repo: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=False)
        svc = UserService(repo)
        assert await svc.delete_user(999) is False
