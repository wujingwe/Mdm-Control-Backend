from unittest.mock import AsyncMock, MagicMock
import pytest
from app.domains.shared.scope import Scope
from app.infra.core.exceptions import ConflictError
from app.domains.mobile_apps.services import MobileAppService
from app.domains.mobile_apps.schemas import MobileAppCreate, MobileAppUpdate


class TestMobileAppService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        m = MagicMock()
        m.list_apps = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock(return_value=0)
        m.get_assignments = AsyncMock(return_value=[])
        m.get_assignment = AsyncMock(return_value=None)
        m.upsert_assignment = AsyncMock()
        return m

    async def test_list_mobile_apps(self, repo: MagicMock) -> None:
        svc = MobileAppService(repo)
        items, total = await svc.list_mobile_apps()
        assert items == []
        assert total == 0

    async def test_list_mobile_apps_paginated(self, repo: MagicMock) -> None:
        svc = MobileAppService(repo)
        await svc.list_mobile_apps(skip=5, limit=15)
        repo.list_apps.assert_called_once_with(skip=5, limit=15)

    async def test_get_mobile_app_found(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = MobileAppService(repo)
        result = await svc.get_mobile_app(1)
        assert result is fake

    async def test_get_mobile_app_not_found(self, repo: MagicMock) -> None:
        svc = MobileAppService(repo)
        result = await svc.get_mobile_app(999)
        assert result is None

    async def test_create_mobile_app(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = MobileAppService(repo)
        result = await svc.create_mobile_app(
            MobileAppCreate(
                name="App",
                enabled=True,
                package_version="1.0",
                package_name="com.app",
                scope=Scope(),
            ),
            created_by=1,
        )
        assert result is fake

    async def test_update_mobile_app(self, repo: MagicMock) -> None:
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = MobileAppService(repo)
        result = await svc.update_mobile_app(1, MobileAppUpdate(name="App2"))
        assert result is fake

    async def test_delete_mobile_app(self, repo: MagicMock) -> None:
        fake = MagicMock()
        fake.scope.targets = []
        repo.get_by_id = AsyncMock(return_value=fake)
        repo.delete = AsyncMock(return_value=True)
        svc = MobileAppService(repo)
        assert await svc.delete_mobile_app(1) is True

    async def test_delete_mobile_app_not_found(self, repo: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=False)
        svc = MobileAppService(repo)
        assert await svc.delete_mobile_app(999) is False

    async def test_delete_with_scope_targets_raises(self, repo: MagicMock) -> None:
        fake = MagicMock()
        fake.scope.targets = [MagicMock()]
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = MobileAppService(repo)
        with pytest.raises(ConflictError):
            await svc.delete_mobile_app(1)

    async def test_get_assignments(self, repo: MagicMock) -> None:
        svc = MobileAppService(repo)
        result = await svc.get_assignments(1)
        assert result == []
        repo.get_assignments.assert_called_once_with(1)

    async def test_update_assignment_status_not_found(self, repo: MagicMock) -> None:
        svc = MobileAppService(repo)
        result = await svc.update_assignment_status(1, 100, "Applied")
        assert result is None
