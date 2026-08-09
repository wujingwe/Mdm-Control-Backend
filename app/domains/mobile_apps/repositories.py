from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.shared.scope import ScopeType, scope_matches
from app.domains.devices.models import Device
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.static_groups.models import StaticGroupDevice
from app.domains.mobile_apps.schemas import MobileAppCreate, MobileAppUpdate, MobileAppAssignmentUpsert


class MobileAppRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_apps(self, skip: int = 0, limit: int = 100) -> list[MobileApp]:
        stmt = select(MobileApp).order_by(MobileApp.id).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, mobile_app_id: int) -> MobileApp | None:
        stmt = select(MobileApp).where(MobileApp.id == mobile_app_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, mobile_app_id: int) -> MobileApp | None:
        stmt = select(MobileApp).where(MobileApp.id == mobile_app_id).with_for_update()
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: MobileAppCreate, created_by: int) -> MobileApp:
        instance = MobileApp(**data.model_dump(), created_by=created_by)
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, mobile_app_id: int, data: MobileAppUpdate) -> int:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return 0
        stmt = update(MobileApp).where(MobileApp.id == mobile_app_id).values(**values, version=MobileApp.version + 1)
        try:
            result = await self._db.execute(stmt)
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return result.rowcount  # type: ignore

    async def delete(self, mobile_app_id: int) -> int:
        stmt = delete(MobileApp).where(MobileApp.id == mobile_app_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        stmt = select(func.count()).select_from(MobileApp)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def get_current_assignments(self, mobile_app_id: int) -> list[MobileAppAssignment]:
        """Return the current assignment for each device.

        The current assignment is the highest version row for the
        (mobile_app_id, device_id) pair.
        """
        max_versions = (
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
                max_versions,
                (MobileAppAssignment.mobile_app_id == mobile_app_id)
                & (MobileAppAssignment.device_id == max_versions.c.device_id)
                & (MobileAppAssignment.version == max_versions.c.max_version),
            )
            .order_by(MobileAppAssignment.device_id)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_current_desired_device_ids(self, mobile_app_id: int) -> set[int]:
        assignments = await self.get_current_assignments(mobile_app_id)
        return {
            assignment.device_id
            for assignment in assignments
            if assignment.desired_state == AssignmentDesiredState.PRESENT
        }

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
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_assignment_by_id(self, assignment_id: int) -> MobileAppAssignment | None:
        stmt = select(MobileAppAssignment).where(MobileAppAssignment.id == assignment_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_assignment_report(
        self,
        assignment_id: int,
        status: AssignmentStatus,
        result_message: str | None = None,
    ) -> None:
        """Record a device's reported status for an assignment."""
        now = datetime.now(timezone.utc)
        values: dict[str, Any] = {"status": status}
        if status == AssignmentStatus.SENT:
            values["acknowledged_at"] = now
        elif status == AssignmentStatus.APPLIED:
            values["completed_at"] = now
            values["applied_at"] = now
        values["last_error"] = result_message if status == AssignmentStatus.FAILED else None
        stmt = update(MobileAppAssignment).where(MobileAppAssignment.id == assignment_id).values(**values)
        await self._db.execute(stmt)
        await self._db.commit()

    async def upsert_assignment(self, data: MobileAppAssignmentUpsert) -> MobileAppAssignment:
        latest = await self.get_assignment(data.mobile_app_id, data.device_id)
        if data.version is None:
            if latest is None:
                raise ValueError("Cannot upsert without a version when no assignment exists")
            version = latest.version
        else:
            version = data.version
        if latest is not None and version < latest.version:
            raise ValueError(f"Cannot upsert assignment at version {version}; latest version is {latest.version}")
        if latest is not None and version == latest.version:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(latest, key, value)
            await self._db.commit()
            await self._db.refresh(latest)
            return latest
        instance = MobileAppAssignment(**data.model_dump())
        self._db.add(instance)
        await self._db.commit()
        await self._db.refresh(instance)
        return instance

    async def list_all_mobile_apps(self) -> list[MobileApp]:
        stmt = select(MobileApp).order_by(MobileApp.id)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def list_mobile_apps_affected_by_device(self, device_id: int) -> list[MobileApp]:
        device = await self._db.get(Device, device_id)
        if device is None:
            return []
        static_group_rows = await self._db.execute(
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
        return affected

    async def get_max_assignment_version(self, mobile_app_id: int) -> int:
        stmt = select(func.coalesce(func.max(MobileAppAssignment.version), 0)).where(
            MobileAppAssignment.mobile_app_id == mobile_app_id
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def bulk_create_assignments(
        self,
        mobile_app_id: int,
        version: int,
        device_ids: set[int],
        revoked_device_ids: set[int] | None = None,
    ) -> None:
        for device_id in device_ids:
            self._db.add(
                MobileAppAssignment(
                    mobile_app_id=mobile_app_id,
                    device_id=device_id,
                    desired_state=AssignmentDesiredState.PRESENT,
                    status=AssignmentStatus.PENDING,
                    version=version,
                )
            )
        for device_id in revoked_device_ids or set():
            self._db.add(
                MobileAppAssignment(
                    mobile_app_id=mobile_app_id,
                    device_id=device_id,
                    desired_state=AssignmentDesiredState.ABSENT,
                    status=AssignmentStatus.REVOKE_PENDING,
                    version=version,
                )
            )

    async def write_revision(
        self,
        app: MobileApp,
        device_ids: set[int],
        revoked_device_ids: set[int] | None = None,
    ) -> int:
        """Persist a new assignment revision for the mobile app and return the version used."""
        latest_version = await self.get_max_assignment_version(app.id)
        version = max(app.version, latest_version + 1 if latest_version else 1)
        app.version = version
        await self.bulk_create_assignments(app.id, version, device_ids, revoked_device_ids=revoked_device_ids)
        await self._db.commit()
        return version

    async def mark_assignment_sent(self, assignment_id: int, message_id: str) -> None:
        assignment = await self._db.get(MobileAppAssignment, assignment_id)
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
            await self._db.commit()

    async def mark_assignment_failed(self, assignment_id: int, error: str) -> None:
        assignment = await self._db.get(MobileAppAssignment, assignment_id)
        if assignment:
            assignment.status = AssignmentStatus.FAILED
            assignment.attempt_count += 1
            assignment.last_attempt_at = datetime.now(timezone.utc)
            assignment.last_error = error[:2000]
            await self._db.commit()

    async def list_mobile_apps_referencing(self, scope_type: ScopeType, target_id: int) -> list[MobileApp]:
        """Return mobile apps whose scope references the given entity as a target or exclusion."""
        apps = await self.list_all_mobile_apps()
        return [app for app in apps if scope_matches(app.scope, scope_type, target_id)]
