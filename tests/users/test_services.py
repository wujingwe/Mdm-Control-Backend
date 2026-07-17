from unittest.mock import AsyncMock, MagicMock
import pytest
from app.users.services import UserService
from app.users.schemas import UserCreate, UserUpdate


class TestUserService:
    @pytest.fixture
    def repo(self):
        m = MagicMock()
        m.list_all = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        return m

    async def test_list_users(self, repo):
        svc = UserService(repo)
        items, total = await svc.list_users()
        assert items == []
        assert total == 0
        repo.list_all.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_list_users_paginated(self, repo):
        svc = UserService(repo)
        await svc.list_users(skip=10, limit=20)
        repo.list_all.assert_called_once_with(skip=10, limit=20)

    async def test_get_user_found(self, repo):
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.get_user(1)
        assert result is fake

    async def test_get_user_not_found(self, repo):
        svc = UserService(repo)
        result = await svc.get_user(999)
        assert result is None

    async def test_create_user(self, repo):
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.create_user(
            UserCreate(email="a@b.com", name="test", password="secret123")
        )
        assert result is fake
        create_arg = repo.create.call_args[0][0]
        assert create_arg.email == "a@b.com"
        assert create_arg.password_hash is not None

    async def test_update_user_with_password(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.update_user(1, UserUpdate(password="newpass"))
        assert result is fake
        update_arg = repo.update.call_args[0][1]
        assert update_arg.password_hash is not None

    async def test_update_user_without_password(self, repo):
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = UserService(repo)
        result = await svc.update_user(1, UserUpdate(name="new name"))
        assert result is fake
        update_arg = repo.update.call_args[0][1]
        assert update_arg.name == "new name"
        assert update_arg.password_hash is None

    async def test_update_user_empty_data(self, repo):
        svc = UserService(repo)
        result = await svc.update_user(1, UserUpdate())
        assert result is None
        repo.update.assert_not_called()

    async def test_delete_user(self, repo):
        repo.delete = AsyncMock(return_value=True)
        svc = UserService(repo)
        assert await svc.delete_user(1) is True
        repo.delete.assert_called_once_with(1)

    async def test_delete_user_not_found(self, repo):
        repo.delete = AsyncMock(return_value=False)
        svc = UserService(repo)
        assert await svc.delete_user(999) is False
