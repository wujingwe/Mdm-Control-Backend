from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest
from app.domains.shared.scope import ScopeType
from app.domains.static_groups.repositories import StaticGroupRepository
from app.domains.static_groups.services import StaticGroupService
from app.domains.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate
from app.infra.core.exceptions import ConflictError


class TestStaticGroupService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        m = MagicMock()
        m.list = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock(return_value=0)
        m.db = AsyncMock()
        return m

    @pytest.fixture
    def profile_repo(self) -> MagicMock:
        m = MagicMock()
        m.list_profiles_referencing = AsyncMock(return_value=[])
        return m

    @pytest.fixture
    def mobile_app_repo(self) -> MagicMock:
        m = MagicMock()
        m.list_mobile_apps_referencing = AsyncMock(return_value=[])
        return m

    @pytest.fixture
    def reconciliation_service(self) -> MagicMock:
        m = MagicMock()
        m.recalculate_profiles_for_group = AsyncMock()
        return m

    async def test_list_groups(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.list_groups()
        assert result == ([], 0)
        repo.list.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_awaited_once()

    async def test_list_groups_paginated(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        await svc.list_groups(skip=5, limit=15)
        repo.list.assert_called_once_with(skip=5, limit=15)

    async def test_get_group_found(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.get_group(1)
        assert result is fake

    async def test_get_group_not_found(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.get_group(999)
        assert result is None

    async def test_create_group(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        fake.id = 7
        repo.create = AsyncMock(return_value=fake)
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        data = StaticGroupCreate(name="G", device_serial_numbers=["SN001"])
        result = await svc.create_group(data, created_by=1)
        assert result is fake
        repo.create.assert_called_once_with(data, 1)
        reconciliation_service.recalculate_profiles_for_group.assert_awaited_once_with(ScopeType.STATIC_GROUP, 7)

    async def test_update_group(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.update_group(1, StaticGroupUpdate(name="G2"))
        assert result is fake
        reconciliation_service.recalculate_profiles_for_group.assert_awaited_once_with(ScopeType.STATIC_GROUP, 1)

    async def test_update_group_not_found(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=0)
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.update_group(1, StaticGroupUpdate(name="G2"))
        assert result == 0
        reconciliation_service.recalculate_profiles_for_group.assert_not_called()

    async def test_delete_group(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        fake.name = "G"
        repo.get_by_id = AsyncMock(return_value=fake)
        repo.delete = AsyncMock(return_value=True)
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        assert await svc.delete_group(1) is True
        repo.delete.assert_awaited_once_with(1)

    async def test_delete_group_not_found(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        assert await svc.delete_group(1) == 0
        repo.delete.assert_not_awaited()

    async def test_delete_group_referenced_by_profile(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        fake.name = "G"
        repo.get_by_id = AsyncMock(return_value=fake)
        profile_repo.list_profiles_referencing = AsyncMock(return_value=[MagicMock(name="P1")])
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        with pytest.raises(ConflictError):
            await svc.delete_group(1)
        repo.delete.assert_not_awaited()

    async def test_delete_group_referenced_by_mobile_app(
        self, repo: MagicMock[StaticGroupRepository], profile_repo: MagicMock, mobile_app_repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        fake.name = "G"
        repo.get_by_id = AsyncMock(return_value=fake)
        mobile_app_repo.list_mobile_apps_referencing = AsyncMock(return_value=[MagicMock(name="App1")])
        svc = StaticGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        with pytest.raises(ConflictError):
            await svc.delete_group(1)
        repo.delete.assert_not_awaited()
