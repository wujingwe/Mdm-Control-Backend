from app.domains.profiles.enums import AssignmentStatus
from app.domains.shared.reconciliation_service import ReconciliationService
from app.domains.shared.scope import ScopeType
from app.infra.core.exceptions import ConflictError
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.mobile_apps.schemas import MobileAppCreate, MobileAppUpdate, MobileAppAssignmentUpsert


class MobileAppService:
    def __init__(self, repo: MobileAppRepository, reconciliation_service: ReconciliationService) -> None:
        self.repo = repo
        self.reconciliation_service = reconciliation_service

    async def list_mobile_apps(self, skip: int = 0, limit: int = 100) -> tuple[list[MobileApp], int]:
        items = await self.repo.list_apps(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_mobile_app(self, mobile_app_id: int) -> MobileApp | None:
        return await self.repo.get_by_id(mobile_app_id)

    async def create_mobile_app(self, data: MobileAppCreate, created_by: int) -> MobileApp:
        app = await self.repo.create(data, created_by)
        if data.scope.targets:
            await self.reconciliation_service.request_recalculate_mobile_app(app.id)
        return app

    async def update_mobile_app(self, mobile_app_id: int, data: MobileAppUpdate) -> int:
        updated = await self.repo.update(mobile_app_id, data)
        if updated and data.scope is not None:
            await self.reconciliation_service.request_recalculate_mobile_app(mobile_app_id)
        return updated

    async def delete_mobile_app(self, mobile_app_id: int) -> int:
        app = await self.repo.get_by_id(mobile_app_id)
        if app is None:
            return 0
        for target in app.scope.targets:
            if target.scope_type == ScopeType.SMART_GROUP and target.target_id:
                await self.reconciliation_service.recalculate_mobile_apps_for_group(
                    ScopeType.SMART_GROUP, target.target_id
                )
            elif target.scope_type == ScopeType.STATIC_GROUP and target.target_id:
                await self.reconciliation_service.recalculate_mobile_apps_for_group(
                    ScopeType.STATIC_GROUP, target.target_id
                )
        if app.scope.targets:
            raise ConflictError("Cannot delete a mobile app with scope targets. Clear the scope first.")
        return await self.repo.delete(mobile_app_id)

    async def get_assignments(self, mobile_app_id: int) -> list[MobileAppAssignment]:
        return await self.repo.get_current_assignments(mobile_app_id)

    async def update_assignment_status(
        self, mobile_app_id: int, device_id: int, status: str
    ) -> MobileAppAssignment | None:
        from datetime import datetime, timezone

        assignment = await self.repo.get_assignment(mobile_app_id, device_id)
        if not assignment:
            return None
        now = datetime.now(timezone.utc)
        status_enum = AssignmentStatus(status)
        return await self.repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=assignment.mobile_app_id,
                device_id=assignment.device_id,
                desired_state=assignment.desired_state,
                version=assignment.version,
                status=status_enum,
                applied_at=now if status_enum == AssignmentStatus.APPLIED else None,
                revoked_at=now if status_enum == AssignmentStatus.REVOKED else None,
            )
        )
