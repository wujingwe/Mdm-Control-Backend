import logging
from collections.abc import Callable
from operator import and_

from sqlalchemy import select
from sqlalchemy.sql.expression import BinaryExpression

from app.common.enums import AssignmentSource, AssignmentStatus, TargetType
from app.devices.models import Device
from app.profiles.models import Profile
from app.profiles.models import ProfileAssignment
from app.profiles.models import ProfileScope
from app.profiles.repositories import ProfileRepository
from app.profiles.schemas import (
    ProfileCreate,
    ProfileUpdate,
    ScopeTarget,
    AssignmentUpsert,
)
from app.static_groups.models import StaticGroupDevice

logger = logging.getLogger(__name__)

_FILTER_BUILDERS: dict[str, Callable] = {
    "is": lambda col, v: col == v,
    "isNot": lambda col, v: col != v,
    "like": lambda col, v: col.like(f"%{v}%"),
    "notLike": lambda col, v: col.not_like(f"%{v}%"),
    "matchesRegex": lambda col, v: col.regexp_match(v),
    "doesNotMatchRegex": lambda col, v: ~col.regexp_match(v),
    "greaterThan": lambda col, v: col.isnot(None) & (col > v),
    "greaterThanOrEqual": lambda col, v: col.isnot(None) & (col >= v),
    "lessThan": lambda col, v: col.isnot(None) & (col < v),
    "lessThanOrEqual": lambda col, v: col.isnot(None) & (col <= v),
}


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

    async def get_scope(self, profile_id: int) -> list[ProfileScope]:
        return await self.repo.get_scope(profile_id)

    async def set_scope(self, profile_id: int, targets: list[ScopeTarget]) -> None:
        await self.repo.set_scope(profile_id, targets)
        await self._recalculate_assignments(profile_id)

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
                source=AssignmentSource(assignment.source),
                source_id=assignment.source_id,
                profile_version=assignment.profile_version,
                status=status_enum,
                applied_at=now if status_enum == AssignmentStatus.APPLIED else None,
                revoked_at=now if status_enum == AssignmentStatus.REVOKED else None,
            )
        )

    async def _recalculate_assignments(self, profile_id: int) -> None:
        db = self.repo.db
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            return

        scope = await self.repo.get_scope(profile_id)
        if not scope:
            await self.repo.delete_non_direct_assignments(profile_id)
            return

        device_ids_by_source: dict[str, dict[int, set[int]]] = {}

        for entry in scope:
            target_type = entry.target_type
            target_id = entry.target_id

            if target_type == TargetType.ALL_DEVICES:
                stmt = select(Device.id)
                result = await db.execute(stmt)
                ids = {row[0] for row in result.all()}
                device_ids_by_source.setdefault(
                    AssignmentSource.ALL_DEVICES, {}
                ).setdefault(0, set()).update(ids)

            elif target_type == TargetType.SMART_GROUP and target_id is not None:
                from app.smart_groups.models import SmartGroup

                sg_stmt = select(SmartGroup).where(SmartGroup.id == target_id)
                sg_result = await db.execute(sg_stmt)
                smart_group = sg_result.scalar_one_or_none()
                if not smart_group or not smart_group.criteria:
                    continue
                criteria_list = (
                    smart_group.criteria
                    if isinstance(smart_group.criteria, list)
                    else []
                )
                filters: list[BinaryExpression] = []
                for c in criteria_list:
                    col = getattr(Device, c.get("field", ""), None)
                    if col is None:
                        continue
                    builder = _FILTER_BUILDERS.get(c.get("operator", "is"))
                    if builder is not None:
                        filters.append(builder(col, c.get("value", "")))
                if filters:
                    where = and_(*filters) if len(filters) > 1 else filters[0]
                    dev_stmt = select(Device.id).where(where)
                else:
                    dev_stmt = select(Device.id)
                dev_result = await db.execute(dev_stmt)
                ids = {row[0] for row in dev_result.all()}
                device_ids_by_source.setdefault(
                    AssignmentSource.SMART_GROUP, {}
                ).setdefault(target_id, set()).update(ids)

            elif target_type == TargetType.STATIC_GROUP and target_id is not None:
                sg_dev_stmt = select(StaticGroupDevice.device_serial_number).where(
                    StaticGroupDevice.static_group_id == target_id
                )
                sg_dev_result = await db.execute(sg_dev_stmt)
                dev_ids = {row[0] for row in sg_dev_result.all()}
                device_ids_by_source.setdefault(
                    AssignmentSource.STATIC_GROUP, {}
                ).setdefault(target_id, set()).update(dev_ids)

            elif target_type == TargetType.DEVICE and target_id is not None:
                device_ids_by_source.setdefault(AssignmentSource.DIRECT, {}).setdefault(
                    0, set()
                ).add(target_id)

        await self.repo.delete_non_direct_assignments(profile_id)

        for source, groups in device_ids_by_source.items():
            for source_id, dev_ids in groups.items():
                for dev_id in dev_ids:
                    await self.repo.upsert_assignment(
                        AssignmentUpsert(
                            profile_id=profile_id,
                            device_id=dev_id,
                            source=AssignmentSource(source),
                            source_id=source_id if source_id else None,
                            status=AssignmentStatus.PENDING,
                            profile_version=profile.version,
                        )
                    )
