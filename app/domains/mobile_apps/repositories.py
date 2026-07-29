from datetime import datetime, timezone

from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.infra.common.enums import AssignmentDesiredState, AssignmentStatus
from app.infra.common.schemas import ScopeType
from app.domains.devices.models import Device
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.static_groups.models import StaticGroupDevice
from app.domains.mobile_apps.schemas import MobileAppCreate, MobileAppUpdate, MobileAppAssignmentUpsert


class MobileAppRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_apps(self, skip: int = 0, limit: int = 100) -> list[MobileApp]:
        stmt = select(MobileApp).order_by(MobileApp.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> MobileApp | None:
        stmt = select(MobileApp).where(MobileApp.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, record_id: int) -> MobileApp | None:
        stmt = select(MobileApp).where(MobileApp.id == record_id).with_for_update()
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: MobileAppCreate, created_by: int) -> MobileApp:
        instance = MobileApp(**data.model_dump(), created_by=created_by)
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, record_id: int, data: MobileAppUpdate) -> MobileApp | None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_by_id(record_id)
        stmt = (
            update(MobileApp)
            .where(MobileApp.id == record_id)
            .values(**values, version=MobileApp.version + 1)
        )
        await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return await self.get_by_id(record_id)

    async def delete(self, record_id: int) -> bool:
        stmt = delete(MobileApp).where(MobileApp.id == record_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def count(self) -> int:
        stmt = select(func.count()).select_from(MobileApp)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_assignments(self, mobile_app_id: int) -> list[MobileAppAssignment]:
        return await self.get_current_assignments(mobile_app_id)

    async def get_current_assignments(self, mobile_app_id: int) -> list[MobileAppAssignment]:
        subq = (
            select(
                MobileAppAssignment.device_id,
                func.max(MobileAppAssignment.version).label("max_version"),
            )
            .where(MobileAppAssignment.mobile_app_id == mobile_app_id)
            .group_by(MobileAppAssignment.device_id)
            .subquery()
        )
        stmt = (
            select(MobileAppAssignment)
            .join(
                subq,
                (MobileAppAssignment.mobile_app_id == mobile_app_id)
                & (MobileAppAssignment.device_id == subq.c.device_id)
                & (MobileAppAssignment.version == subq.c.max_version),
            )
            .order_by(MobileAppAssignment.device_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_current_desired_device_ids(self, mobile_app_id: int) -> set[int]:
        assignments = await self.get_current_assignments(mobile_app_id)
        return {
            assignment.device_id
            for assignment in assignments
            if assignment.desired_state == AssignmentDesiredState.PRESENT
        }

    async def get_current_assignments_for_device(self, device_id: int) -> list[MobileAppAssignment]:
        subq = (
            select(
                MobileAppAssignment.mobile_app_id,
                func.max(MobileAppAssignment.version).label("max_version"),
            )
            .where(MobileAppAssignment.device_id == device_id)
            .group_by(MobileAppAssignment.mobile_app_id)
            .subquery()
        )
        stmt = (
            select(MobileAppAssignment)
            .join(
                subq,
                (MobileAppAssignment.device_id == device_id)
                & (MobileAppAssignment.mobile_app_id == subq.c.mobile_app_id)
                & (MobileAppAssignment.version == subq.c.max_version),
            )
            .order_by(MobileAppAssignment.mobile_app_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_assignment(self, mobile_app_id: int, device_id: int) -> MobileAppAssignment | None:
        stmt = (
            select(MobileAppAssignment)
            .where(
                MobileAppAssignment.mobile_app_id == mobile_app_id,
                MobileAppAssignment.device_id == device_id,
            )
            .order_by(MobileAppAssignment.version.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_assignment_by_version(
        self, mobile_app_id: int, device_id: int, version: int
    ) -> MobileAppAssignment | None:
        stmt = select(MobileAppAssignment).where(
            MobileAppAssignment.mobile_app_id == mobile_app_id,
            MobileAppAssignment.device_id == device_id,
            MobileAppAssignment.version == version,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_assignment(self, data: MobileAppAssignmentUpsert) -> MobileAppAssignment:
        existing = await self.get_assignment_by_version(data.mobile_app_id, data.device_id, data.version)
        if existing:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        instance = MobileAppAssignment(**data.model_dump())
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def bulk_upsert_assignments(self, mobile_app_id: int, assignments: list[MobileAppAssignmentUpsert]) -> int:
        count = 0
        for data in assignments:
            existing = await self.get_assignment_by_version(data.mobile_app_id, data.device_id, data.version)
            if existing:
                for key, value in data.model_dump(exclude_unset=True).items():
                    setattr(existing, key, value)
            else:
                self.db.add(MobileAppAssignment(**data.model_dump()))
            count += 1
        await self.db.commit()
        return count

    async def list_all_mobile_apps(self) -> list[MobileApp]:
        stmt = select(MobileApp).order_by(MobileApp.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_affected_mobile_apps_for_device(self, device_id: int) -> list[MobileApp]:
        device = await self.db.get(Device, device_id)
        if device is None:
            return []
        static_group_rows = await self.db.execute(
            select(StaticGroupDevice.static_group_id).where(
                StaticGroupDevice.device_serial_number == device.serial_number
            )
        )
        static_group_ids = {row[0] for row in static_group_rows.all()}

        apps = await self.list_all_mobile_apps()
        affected: list[MobileApp] = []
        for app in apps:
            scope = app.scope
            for target in scope.targets:
                if target.scope_type == ScopeType.ALL_DEVICES:
                    affected.append(app)
                    break
                if target.scope_type == ScopeType.DEVICE and target.target_id == device_id:
                    affected.append(app)
                    break
                if target.scope_type == ScopeType.SMART_GROUP:
                    affected.append(app)
                    break
                if target.scope_type == ScopeType.STATIC_GROUP and target.target_id in static_group_ids:
                    affected.append(app)
                    break
            else:
                for exclusion in scope.exclusions:
                    if exclusion.scope_type == ScopeType.SMART_GROUP:
                        affected.append(app)
                        break
                    if (exclusion.scope_type == ScopeType.DEVICE and exclusion.exclude_id == device_id) or (
                        exclusion.scope_type == ScopeType.STATIC_GROUP and exclusion.exclude_id in static_group_ids
                    ):
                        affected.append(app)
                        break
        return affected

    async def get_max_assignment_version(self, mobile_app_id: int) -> int:
        stmt = select(func.coalesce(func.max(MobileAppAssignment.version), 0)).where(
            MobileAppAssignment.mobile_app_id == mobile_app_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_assignment_device_ids_at_version(self, mobile_app_id: int, version: int) -> set[int]:
        stmt = select(MobileAppAssignment.device_id).where(
            MobileAppAssignment.mobile_app_id == mobile_app_id,
            MobileAppAssignment.version == version,
        )
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all()}

    async def bulk_create_assignments(
        self,
        mobile_app_id: int,
        version: int,
        device_ids: set[int],
        revoked_device_ids: set[int] | None = None,
    ) -> None:
        for device_id in device_ids:
            self.db.add(
                MobileAppAssignment(
                    mobile_app_id=mobile_app_id,
                    device_id=device_id,
                    desired_state=AssignmentDesiredState.PRESENT,
                    status=AssignmentStatus.PENDING,
                    version=version,
                )
            )
        for device_id in revoked_device_ids or set():
            self.db.add(
                MobileAppAssignment(
                    mobile_app_id=mobile_app_id,
                    device_id=device_id,
                    desired_state=AssignmentDesiredState.ABSENT,
                    status=AssignmentStatus.REVOKE_PENDING,
                    version=version,
                )
            )

    async def mark_assignment_sent(self, assignment_id: int, message_id: str) -> None:
        assignment = await self.db.get(MobileAppAssignment, assignment_id)
        if assignment:
            assignment.status = (
                AssignmentStatus.REVOKE_PENDING
                if assignment.desired_state == AssignmentDesiredState.ABSENT
                else AssignmentStatus.SENT
            )
            assignment.message_id = message_id
            assignment.attempt_count += 1
            assignment.last_attempt_at = datetime.now(timezone.utc)
            assignment.last_error = None
            await self.db.commit()

    async def mark_assignment_failed(self, assignment_id: int, error: str) -> None:
        assignment = await self.db.get(MobileAppAssignment, assignment_id)
        if assignment:
            assignment.status = AssignmentStatus.FAILED
            assignment.attempt_count += 1
            assignment.last_attempt_at = datetime.now(timezone.utc)
            assignment.last_error = error[:2000]
            await self.db.commit()

    async def remove_scope_references(self, scope_type: ScopeType, target_id: int) -> list[int]:
        apps = await self.list_all_mobile_apps()
        affected: list[int] = []
        for app in apps:
            modified = False
            original_targets = list(app.scope.targets)
            original_exclusions = list(app.scope.exclusions)
            new_targets = [
                t for t in original_targets if not (t.scope_type == scope_type and (t.target_id or 0) == target_id)
            ]
            new_exclusions = [
                e for e in original_exclusions if not (e.scope_type == scope_type and (e.exclude_id or 0) == target_id)
            ]
            if len(new_targets) != len(original_targets):
                app.scope.targets = new_targets
                modified = True
            if len(new_exclusions) != len(original_exclusions):
                app.scope.exclusions = new_exclusions
                modified = True
            if modified:
                flag_modified(app, "scope")
                affected.append(app.id)
        if affected:
            await self.db.commit()
        return affected
