from unittest.mock import AsyncMock, MagicMock
import pytest
from app.domains.shared.scope import Scope, ScopeTarget, ScopeType
from app.domains.profiles.schemas.policy import Policy
from app.domains.profiles.services import ProfileService
from app.domains.profiles.schemas.profile import ProfileCreate, ProfileUpdate


class TestProfileService:
    @pytest.fixture
    def repo(self) -> None:
        m = MagicMock()
        m.list_profiles = AsyncMock(return_value=[])
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
        m.request_recalculate_profile = AsyncMock()
        return m

    def _scoped(self) -> Scope:
        return Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)])

    async def test_list_profiles(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = ProfileService(repo, reconciliation_service)
        items, total = await svc.list_profiles()
        assert items == []
        assert total == 0

    async def test_list_profiles_paginated(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = ProfileService(repo, reconciliation_service)
        await svc.list_profiles(skip=5, limit=15)
        repo.list_profiles.assert_called_once_with(skip=5, limit=15)

    async def test_get_profile_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.get_profile(1)
        assert result is fake

    async def test_get_profile_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.get_profile(999)
        assert result is None

    async def test_create_profile(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        fake = MagicMock()
        repo.create = AsyncMock(return_value=fake)
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.create_profile(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        assert result is fake
        reconciliation_service.request_recalculate_profile.assert_not_called()

    async def test_create_profile_with_scope_triggers_recalculation(
        self, repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        fake = MagicMock()
        fake.id = 7
        repo.create = AsyncMock(return_value=fake)
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.create_profile(ProfileCreate(name="P", policy=Policy(), scope=self._scoped()), created_by=1)
        assert result is fake
        reconciliation_service.request_recalculate_profile.assert_awaited_once_with(7)

    async def test_update_profile(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.update_profile(1, ProfileUpdate(name="P2"))
        assert result == 1
        reconciliation_service.request_recalculate_profile.assert_not_called()

    async def test_update_profile_with_scope_triggers_recalculation(
        self, repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.update_profile(1, ProfileUpdate(scope=self._scoped()))
        assert result == 1
        reconciliation_service.request_recalculate_profile.assert_awaited_once_with(1, force_push=False)

    async def test_update_profile_with_policy_forces_push(
        self, repo: MagicMock, reconciliation_service: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.update_profile(1, ProfileUpdate(policy=Policy()))
        assert result == 1
        reconciliation_service.request_recalculate_profile.assert_awaited_once_with(1, force_push=True)

    async def test_update_profile_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        repo.update = AsyncMock(return_value=0)
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.update_profile(1, ProfileUpdate(scope=self._scoped()))
        assert result == 0
        reconciliation_service.request_recalculate_profile.assert_not_called()

    async def test_delete_profile(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        fake = MagicMock()
        fake.scope.targets = []
        repo.get_by_id = AsyncMock(return_value=fake)
        repo.delete = AsyncMock(return_value=1)
        svc = ProfileService(repo, reconciliation_service)
        assert await svc.delete_profile(1) == 1

    async def test_delete_profile_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        repo.delete = AsyncMock(return_value=0)
        svc = ProfileService(repo, reconciliation_service)
        assert await svc.delete_profile(999) == 0

    async def test_get_assignments(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.get_assignments(1)
        assert result == []
        repo.get_current_assignments.assert_called_once_with(1)

    async def test_update_assignment_status_not_found(self, repo: MagicMock, reconciliation_service: MagicMock) -> None:
        svc = ProfileService(repo, reconciliation_service)
        result = await svc.update_assignment_status(1, 100, "Applied")
        assert result is None
