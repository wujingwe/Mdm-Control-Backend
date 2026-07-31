from typing import Any, Generic, Protocol, TypeVar

from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.repositories import ProfileRepository
from app.domains.shared.reconciliation_service import ReconciliationService
from app.domains.shared.scope import ScopeType
from app.infra.core.exceptions import ConflictError

T = TypeVar("T", bound="NamedEntity")


class NamedEntity(Protocol):
    id: Any
    name: Any


class GroupRepositoryProtocol(Protocol[T]):
    async def list(self, skip: int = 0, limit: int = 100) -> list[T]: ...
    async def get_by_id(self, record_id: int) -> T | None: ...
    async def create(self, data: Any, created_by: int) -> T: ...
    async def update(self, record_id: int, data: Any) -> int: ...
    async def delete(self, record_id: int) -> int: ...
    async def count(self) -> int: ...


class GroupScopeService(Generic[T]):
    scope_type: ScopeType
    entity_label: str

    def __init__(
        self,
        repo: GroupRepositoryProtocol[T],
        profile_repo: ProfileRepository,
        mobile_app_repo: MobileAppRepository,
        reconciliation_service: ReconciliationService,
    ) -> None:
        self.repo = repo
        self.profile_repo = profile_repo
        self.mobile_app_repo = mobile_app_repo
        self.reconciliation_service = reconciliation_service

    async def list_groups(self, skip: int = 0, limit: int = 100) -> tuple[list[T], int]:
        items = await self.repo.list(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_group(self, group_id: int) -> T | None:
        return await self.repo.get_by_id(group_id)

    async def create_group(self, data: Any, created_by: int) -> T:
        group = await self.repo.create(data, created_by)
        if group:
            await self.reconciliation_service.recalculate_profiles_for_group(self.scope_type, group.id)
        return group

    async def update_group(self, group_id: int, data: Any) -> int:
        updated = await self.repo.update(group_id, data)
        if updated:
            await self.reconciliation_service.recalculate_profiles_for_group(self.scope_type, group_id)
        return updated

    async def delete_group(self, group_id: int) -> int:
        group = await self.repo.get_by_id(group_id)
        if group is None:
            return 0
        references = await self._list_scope_reference_labels(self.scope_type, group_id)
        if references:
            raise ConflictError(
                f"Cannot delete {self.entity_label} '{group.name}' "
                f"while it is still referenced by: {', '.join(references)}."
            )
        return await self.repo.delete(group_id)

    async def _list_scope_reference_labels(self, scope_type: ScopeType, group_id: int) -> list[str]:
        profiles = await self.profile_repo.list_profiles_referencing(scope_type, group_id)
        apps = await self.mobile_app_repo.list_mobile_apps_referencing(scope_type, group_id)
        return [f"profile '{p.name}'" for p in profiles] + [f"mobile app '{a.name}'" for a in apps]
