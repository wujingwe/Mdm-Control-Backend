from unittest.mock import AsyncMock, MagicMock
import pytest
from app.domains.shared.scope import Scope, ScopeTarget, ScopeType
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
        m.get_current_assignments = AsyncMock(return_value=[])
        m.get_assignment = AsyncMock(return_value=None)
        m.upsert_assignment = AsyncMock()
        return m

    @pytest.fixture
    def reconciliation_service(self) -> MagicMock:
        m = MagicMock()
        m.request_recalculate_mobile_app = AsyncMock()
        m.recalculate_mobile_apps_for_group = AsyncMock()
        return m

    @staticmethod
    def _scoped() -> Scope:
        return Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)])

    @staticmethod
    def _create_data(*, scope: Scope | None = None) -> MobileAppCreate:
        return MobileAppCreate(
            name="App",
            enabled=True,
            package_version="1.0",
            package_name="com.app",
            scope=scope or Scope(),
        )

    async def test_list_mobile_apps(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = MobileAppService(repo, reconciliation_service)
        items, total = await svc.list_mobile_apps()
        assert items == []
        assert total == 0

    async def test_list_mobile_apps_paginated(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = MobileAppService(repo, reconciliation_service)
        await svc.list_mobile_apps(skip=5, limit=15)
        repo.list_apps.assert_called_once_with(skip=5, limit=15)

    async def test_get_mobile_app_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = MobileAppService(repo, reconciliation_service)
        result = await svc.get_mobile_app(1)
        assert result is fake

    async def test_get_mobile_app_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = MobileAppService(repo, reconciliation_service)
        result = await svc.get_mobile_app(999)
        assert result is None

    async def test_create_mobile_app(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = MobileAppService(repo, reconciliation_service)
        result = await svc.create_mobile_app(self._create_data(), created_by=1)
        assert result is fake
        reconciliation_service.request_recalculate_mobile_app.assert_not_called()

    async def test_create_mobile_app_with_scope_triggers_recalculation(
        self, repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        fake.id = 7
        repo.create = AsyncMock(return_value=fake)
        svc = MobileAppService(repo, reconciliation_service)
        result = await svc.create_mobile_app(self._create_data(scope=self._scoped()), created_by=1)
        assert result is fake
        reconciliation_service.request_recalculate_mobile_app.assert_awaited_once_with(7)

    async def test_update_mobile_app(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = MobileAppService(repo, reconciliation_service)
        result = await svc.update_mobile_app(1, MobileAppUpdate(name="App2"))
        assert result == 1
        reconciliation_service.request_recalculate_mobile_app.assert_not_called()

    async def test_update_mobile_app_with_scope_triggers_recalculation(
        self, repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = MobileAppService(repo, reconciliation_service)
        result = await svc.update_mobile_app(1, MobileAppUpdate(scope=self._scoped()))
        assert result == 1
        reconciliation_service.request_recalculate_mobile_app.assert_awaited_once_with(1)

    async def test_delete_mobile_app(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        fake = MagicMock()
        fake.scope.targets = []
        repo.get_by_id = AsyncMock(return_value=fake)
        repo.delete = AsyncMock(return_value=1)
        svc = MobileAppService(repo, reconciliation_service)
        assert await svc.delete_mobile_app(1) == 1

    async def test_delete_mobile_app_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=0)
        svc = MobileAppService(repo, reconciliation_service)
        assert await svc.delete_mobile_app(999) == 0

    async def test_delete_with_scope_targets_raises(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        fake = MagicMock()
        fake.scope.targets = [MagicMock()]
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = MobileAppService(repo, reconciliation_service)
        with pytest.raises(ConflictError):
            await svc.delete_mobile_app(1)

    async def test_delete_with_smart_group_target_recalculates_group(
        self, repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        target = MagicMock()
        target.scope_type = ScopeType.SMART_GROUP
        target.target_id = 3
        fake.scope.targets = [target]
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = MobileAppService(repo, reconciliation_service)
        with pytest.raises(ConflictError):
            await svc.delete_mobile_app(1)
        reconciliation_service.recalculate_mobile_apps_for_group.assert_awaited_once_with(ScopeType.SMART_GROUP, 3)

    async def test_get_assignments(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = MobileAppService(repo, reconciliation_service)
        result = await svc.get_assignments(1)
        assert result == []
        repo.get_current_assignments.assert_called_once_with(1)

    async def test_update_assignment_status_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = MobileAppService(repo, reconciliation_service)
        result = await svc.update_assignment_status(1, 100, "Applied")
        assert result is None
