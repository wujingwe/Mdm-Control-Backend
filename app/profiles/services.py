import logging

from sqlalchemy import select

from app.common.enums import AssignmentStatus
from app.common.schemas import Scope, ScopeType
from app.criteria import build_device_query
from app.devices.models import Device
from app.profiles.calculator import AssignmentCalculator
from app.profiles.models import Profile, ProfileAssignment
from app.profiles.repositories import ProfileRepository
from app.profiles.schemas import ProfileCreate, ProfileUpdate, AssignmentUpsert
from app.static_groups.models import StaticGroupDevice

logger = logging.getLogger(__name__)


class ProfileService:
    def __init__(self, repo: ProfileRepository) -> None:
        self.repo = repo

    async def list_profiles(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[Profile], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_profile(self, profile_id: int) -> Profile | None:
        return await self.repo.get_by_id(profile_id)

    async def create_profile(self, data: ProfileCreate) -> Profile:
        return await self.repo.create(data)

    async def update_profile(
        self, profile_id: int, data: ProfileUpdate
    ) -> Profile | None:
        return await self.repo.update(profile_id, data)

    async def delete_profile(self, profile_id: int) -> bool:
        return await self.repo.delete(profile_id)

    async def get_assignments(self, profile_id: int) -> list[ProfileAssignment]:
        return await self.repo.get_assignments(profile_id)

    async def update_assignment_status(
        self, profile_id: int, device_id: int, status: str
    ) -> ProfileAssignment | None:
        from datetime import datetime, timezone

        assignment = await self.repo.get_assignment(profile_id, device_id)
        if not assignment:
            return None
        now = datetime.now(timezone.utc)
        status_enum = AssignmentStatus(status)
        return await self.repo.upsert_assignment(
            AssignmentUpsert(
                profile_id=assignment.profile_id,
                device_id=assignment.device_id,
                profile_version=assignment.profile_version,
                status=status_enum,
                applied_at=now if status_enum == AssignmentStatus.APPLIED else None,
                revoked_at=now if status_enum == AssignmentStatus.REVOKED else None,
            )
        )

    async def recalculate_assignments(self, profile_id: int) -> None:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            return

        if not profile.scope.targets:
            await self.repo.delete_old_version_assignments(
                profile_id, profile.version
            )
            return

        resolved = await self._resolve_scope(profile_id, profile.scope)
        assignments = AssignmentCalculator.compute(
            profile_id=profile_id,
            profile_version=profile.version,
            scope=profile.scope,
            resolved_device_ids=resolved,
        )

        await self.repo.delete_old_version_assignments(profile_id, profile.version)
        await self.repo.bulk_upsert_assignments(profile_id, assignments)

    async def _resolve_scope(
        self, profile_id: int, scope: Scope
    ) -> dict[tuple[str, int], set[int | str]]:
        db = self.repo.db
        result: dict[tuple[str, int], set[int | str]] = {}

        for target in scope.targets:
            if target.scope_type == ScopeType.ALL_DEVICES:
                stmt = select(Device.id)
                rows = await db.execute(stmt)
                result[(ScopeType.ALL_DEVICES.value, 0)] = {
                    row[0] for row in rows.all()
                }

            elif target.scope_type == ScopeType.SMART_GROUP and target.target_id:
                from app.smart_groups.models import SmartGroup

                sg_stmt = select(SmartGroup).where(
                    SmartGroup.id == target.target_id
                )
                sg_result = await db.execute(sg_stmt)
                smart_group = sg_result.scalar_one_or_none()
                if not smart_group or not smart_group.criteria:
                    continue
                criteria_list = (
                    smart_group.criteria
                    if isinstance(smart_group.criteria, list)
                    else []
                )
                where, _ = build_device_query(criteria_list)
                dev_stmt = (
                    select(Device.id).where(where) if where else select(Device.id)
                )
                dev_result = await db.execute(dev_stmt)
                result[(ScopeType.SMART_GROUP.value, target.target_id)] = {
                    row[0] for row in dev_result.all()
                }

            elif target.scope_type == ScopeType.STATIC_GROUP and target.target_id:
                sg_dev_stmt = select(StaticGroupDevice.device_serial_number).where(
                    StaticGroupDevice.static_group_id == target.target_id
                )
                sg_dev_result = await db.execute(sg_dev_stmt)
                result[(ScopeType.STATIC_GROUP.value, target.target_id)] = {
                    row[0] for row in sg_dev_result.all()
                }

            elif target.scope_type == ScopeType.DEVICE and target.target_id:
                result[(ScopeType.DEVICE.value, target.target_id)] = {
                    target.target_id
                }

        for exclusion in scope.exclusions:
            if exclusion.scope_type == ScopeType.SMART_GROUP and exclusion.exclude_id:
                from app.smart_groups.models import SmartGroup

                sg_stmt = select(SmartGroup).where(
                    SmartGroup.id == exclusion.exclude_id
                )
                sg_result = await db.execute(sg_stmt)
                smart_group = sg_result.scalar_one_or_none()
                if not smart_group or not smart_group.criteria:
                    continue
                criteria_list = (
                    smart_group.criteria
                    if isinstance(smart_group.criteria, list)
                    else []
                )
                where, _ = build_device_query(criteria_list)
                dev_stmt = (
                    select(Device.id).where(where) if where else select(Device.id)
                )
                dev_result = await db.execute(dev_stmt)
                result[(ScopeType.SMART_GROUP.value, exclusion.exclude_id)] = {
                    row[0] for row in dev_result.all()
                }

            elif exclusion.scope_type == ScopeType.STATIC_GROUP and exclusion.exclude_id:
                sg_dev_stmt = select(StaticGroupDevice.device_serial_number).where(
                    StaticGroupDevice.static_group_id == exclusion.exclude_id
                )
                sg_dev_result = await db.execute(sg_dev_stmt)
                result[(ScopeType.STATIC_GROUP.value, exclusion.exclude_id)] = {
                    row[0] for row in sg_dev_result.all()
                }

        return result
