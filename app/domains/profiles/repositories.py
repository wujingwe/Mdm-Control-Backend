from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.shared.scope import ScopeType, scope_matches
from app.domains.devices.models import Device
from app.domains.profiles.models import Profile, ProfileAssignment
from app.domains.static_groups.models import StaticGroupDevice
from app.domains.profiles.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    AssignmentUpsert,
)


class ProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_profiles(self, skip: int = 0, limit: int = 100) -> list[Profile]:
        stmt = select(Profile).order_by(Profile.id).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, profile_id: int) -> Profile | None:
        stmt = select(Profile).where(Profile.id == profile_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, profile_id: int) -> Profile | None:
        stmt = select(Profile).where(Profile.id == profile_id).with_for_update()
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: ProfileCreate, created_by: int) -> Profile:
        instance = Profile(**data.model_dump(), created_by=created_by)
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Profile with this name already exists") from err
        return instance

    async def update(self, record_id: int, data: ProfileUpdate) -> int:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return 0
        stmt = update(Profile).where(Profile.id == record_id).values(**values)
        try:
            result = await self._db.execute(stmt)
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Profile with this name already exists") from err
        return result.rowcount  # type: ignore

    async def delete(self, record_id: int) -> int:
        stmt = delete(Profile).where(Profile.id == record_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Profile)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def get_current_assignments(self, profile_id: int) -> list[ProfileAssignment]:
        """Return the current assignment for each device.

        The current assignment is the highest profile_version row for the
        (profile_id, device_id) pair.
        """
        max_versions = (
            select(
                ProfileAssignment.device_id,
                func.max(ProfileAssignment.profile_version).label("max_version"),
            )
            .where(ProfileAssignment.profile_id == profile_id)
            .group_by(ProfileAssignment.device_id)
            .subquery()
        )

        stmt = (
            select(ProfileAssignment)
            .join(
                max_versions,
                (ProfileAssignment.profile_id == profile_id)
                & (ProfileAssignment.device_id == max_versions.c.device_id)
                & (ProfileAssignment.profile_version == max_versions.c.max_version),
            )
            .order_by(ProfileAssignment.device_id)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_current_desired_device_ids(self, profile_id: int) -> set[int]:
        assignments = await self.get_current_assignments(profile_id)
        return {
            assignment.device_id
            for assignment in assignments
            if assignment.desired_state == AssignmentDesiredState.PRESENT
        }

    async def get_assignment(self, profile_id: int, device_id: int) -> ProfileAssignment | None:
        stmt = (
            select(ProfileAssignment)
            .where(
                ProfileAssignment.profile_id == profile_id,
                ProfileAssignment.device_id == device_id,
            )
            .order_by(ProfileAssignment.profile_version.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_assignment_by_id(self, assignment_id: int) -> ProfileAssignment | None:
        stmt = select(ProfileAssignment).where(ProfileAssignment.id == assignment_id)
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
        stmt = update(ProfileAssignment).where(ProfileAssignment.id == assignment_id).values(**values)
        await self._db.execute(stmt)
        await self._db.commit()

    async def upsert_assignment(self, data: AssignmentUpsert) -> ProfileAssignment:
        latest = await self.get_assignment(data.profile_id, data.device_id)
        if data.profile_version is None:
            if latest is None:
                raise ValueError("Cannot upsert without a profile_version when no assignment exists")
            version = latest.profile_version
        else:
            version = data.profile_version
        if latest is not None and version < latest.profile_version:
            raise ValueError(
                f"Cannot upsert assignment at version {version}; latest version is {latest.profile_version}"
            )
        if latest is not None and version == latest.profile_version:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(latest, key, value)
            await self._db.commit()
            await self._db.refresh(latest)
            return latest
        instance = ProfileAssignment(**data.model_dump())
        self._db.add(instance)
        await self._db.commit()
        await self._db.refresh(instance)
        return instance

    async def list_all_profiles(self) -> list[Profile]:
        stmt = select(Profile).order_by(Profile.id)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def list_profiles_affected_by_device(self, device_id: int) -> list[Profile]:
        device = await self._db.get(Device, device_id)
        if device is None:
            return []

        static_group_rows = await self._db.execute(
            select(StaticGroupDevice.static_group_id).where(
                StaticGroupDevice.device_serial_number == device.serial_number
            )
        )
        static_group_ids = {row[0] for row in static_group_rows.all()}

        profiles = await self.list_all_profiles()
        affected: list[Profile] = []
        for profile in profiles:
            scope = profile.scope
            for target in scope.targets:
                if target.scope_type == ScopeType.ALL_DEVICES:
                    affected.append(profile)
                    break
                if target.scope_type == ScopeType.DEVICE and target.target_id == device_id:
                    affected.append(profile)
                    break
                if target.scope_type == ScopeType.SMART_GROUP:
                    affected.append(profile)
                    break
                if target.scope_type == ScopeType.STATIC_GROUP and target.target_id in static_group_ids:
                    affected.append(profile)
                    break
        return affected

    async def get_max_assignment_version(self, profile_id: int) -> int:
        stmt = select(func.coalesce(func.max(ProfileAssignment.profile_version), 0)).where(
            ProfileAssignment.profile_id == profile_id
        )
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def bulk_create_assignments(
        self,
        profile_id: int,
        version: int,
        device_ids: set[int],
        revoked_device_ids: set[int] | None = None,
    ) -> None:
        for device_id in device_ids:
            self._db.add(
                ProfileAssignment(
                    profile_id=profile_id,
                    device_id=device_id,
                    desired_state=AssignmentDesiredState.PRESENT,
                    status=AssignmentStatus.PENDING,
                    profile_version=version,
                )
            )
        for device_id in revoked_device_ids or set():
            self._db.add(
                ProfileAssignment(
                    profile_id=profile_id,
                    device_id=device_id,
                    desired_state=AssignmentDesiredState.ABSENT,
                    status=AssignmentStatus.REVOKE_PENDING,
                    profile_version=version,
                )
            )

    async def write_revision(
        self,
        profile: Profile,
        device_ids: set[int],
        revoked_device_ids: set[int] | None = None,
    ) -> int:
        """Persist a new assignment revision for the profile and return the version used."""
        latest_version = await self.get_max_assignment_version(profile.id)
        version = max(profile.version, latest_version + 1 if latest_version else 1)
        profile.version = version
        await self.bulk_create_assignments(profile.id, version, device_ids, revoked_device_ids=revoked_device_ids)
        await self._db.commit()
        return version

    async def mark_assignment_sent(self, assignment_id: int, message_id: str) -> None:
        assignment = await self._db.get(ProfileAssignment, assignment_id)
        if not assignment:
            return

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
        assignment = await self._db.get(ProfileAssignment, assignment_id)
        if not assignment:
            return

        assignment.status = AssignmentStatus.FAILED
        assignment.attempt_count += 1
        assignment.last_attempt_at = datetime.now(timezone.utc)
        assignment.last_error = error[:2000]
        await self._db.commit()

    async def list_profiles_referencing(self, scope_type: ScopeType, target_id: int) -> list[Profile]:
        """Return profiles whose scope references the given entity as a target or exclusion."""
        profiles = await self.list_all_profiles()
        return [profile for profile in profiles if scope_matches(profile.scope, scope_type, target_id)]
