from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.domains.devices.criteria import CriteriaType
from app.infra.criteria import Criteria
from app.domains.shared.scope import ScopeType
from app.domains.smart_groups.services import SmartGroupService
from app.domains.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate
from app.infra.core.exceptions import ConflictError


class TestSmartGroupService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        m = MagicMock()
        m.list = AsyncMock(return_value=[])
        m.get_by_id = AsyncMock(return_value=None)
        m.create = AsyncMock()
        m.update = AsyncMock()
        m.delete = AsyncMock()
        m.count = AsyncMock()
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
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        await svc.list_groups()
        repo.list.assert_called_once_with(skip=0, limit=100)

    async def test_get_group(
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.get_group(1)
        assert result is fake

    async def test_create_group(
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        fake = MagicMock()
        fake.id = 7
        repo.create = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.create_group(
            SmartGroupCreate(
                name="G",
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
        assert result is fake
        reconciliation_service.recalculate_profiles_for_group.assert_awaited_once_with(ScopeType.SMART_GROUP, 7)

    async def test_update_group(
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        fake = MagicMock()
        repo.update = AsyncMock(return_value=fake)
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.update_group(1, SmartGroupUpdate(name="G2"))
        assert result is fake
        reconciliation_service.recalculate_profiles_for_group.assert_awaited_once_with(ScopeType.SMART_GROUP, 1)

    async def test_update_group_not_found(
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        repo.update = AsyncMock(return_value=0)
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        result = await svc.update_group(1, SmartGroupUpdate(name="G2"))
        assert result == 0
        reconciliation_service.recalculate_profiles_for_group.assert_not_called()

    async def test_delete_group(
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        fake = MagicMock()
        fake.name = "G"
        repo.get_by_id = AsyncMock(return_value=fake)
        repo.delete = AsyncMock(return_value=True)
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        assert await svc.delete_group(1) is True
        repo.delete.assert_awaited_once_with(1)

    async def test_delete_group_not_found(
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        assert await svc.delete_group(1) == 0
        repo.delete.assert_not_awaited()

    async def test_delete_group_referenced_by_profile(
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        fake = MagicMock()
        fake.name = "G"
        repo.get_by_id = AsyncMock(return_value=fake)
        profile_repo.list_profiles_referencing = AsyncMock(return_value=[MagicMock(name="P1")])
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        with pytest.raises(ConflictError):
            await svc.delete_group(1)
        repo.delete.assert_not_awaited()

    async def test_delete_group_referenced_by_mobile_app(
        self,
        repo: MagicMock[SmartGroupService],
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
        reconciliation_service: MagicMock,
    ) -> None:
        fake = MagicMock()
        fake.name = "G"
        repo.get_by_id = AsyncMock(return_value=fake)
        mobile_app_repo.list_mobile_apps_referencing = AsyncMock(return_value=[MagicMock(name="App1")])
        svc = SmartGroupService(repo, profile_repo, mobile_app_repo, reconciliation_service)
        with pytest.raises(ConflictError):
            await svc.delete_group(1)
        repo.delete.assert_not_awaited()
