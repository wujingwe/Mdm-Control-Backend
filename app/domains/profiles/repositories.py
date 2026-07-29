from datetime import datetime, timezone

from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.infra.common.enums import AssignmentDesiredState, AssignmentStatus
from app.infra.common.schemas import ScopeType
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
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Profile]:
        stmt = select(Profile).order_by(Profile.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> Profile | None:
        stmt = select(Profile).where(Profile.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, record_id: int) -> Profile | None:
        stmt = select(Profile).where(Profile.id == record_id).with_for_update()
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: ProfileCreate, created_by: int) -> Profile:
        instance = Profile(**data.model_dump(), created_by=created_by)
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Profile with this name already exists") from err
        return instance

    async def update(self, record_id: int, data: ProfileUpdate) -> Profile | None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_by_id(record_id)
        stmt = update(Profile).where(Profile.id == record_id).values(**values)
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Profile with this name already exists") from err
        return await self.get_by_id(record_id)

    async def delete(self, record_id: int) -> bool:
        stmt = delete(Profile).where(Profile.id == record_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Profile)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_assignments(self, profile_id: int) -> list[ProfileAssignment]:
        return await self.get_current_assignments(profile_id)

    async def get_current_assignments(self, profile_id: int) -> list[ProfileAssignment]:
        subq = (
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
                subq,
                (ProfileAssignment.profile_id == profile_id)
                & (ProfileAssignment.device_id == subq.c.device_id)
                & (ProfileAssignment.profile_version == subq.c.max_version),
            )
            .order_by(ProfileAssignment.device_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_current_desired_device_ids(self, profile_id: int) -> set[int]:
        assignments = await self.get_current_assignments(profile_id)
        return {
            assignment.device_id
            for assignment in assignments
            if assignment.desired_state == AssignmentDesiredState.PRESENT
        }

    async def get_current_assignments_for_device(self, device_id: int) -> list[ProfileAssignment]:
        subq = (
            select(
                ProfileAssignment.profile_id,
                func.max(ProfileAssignment.profile_version).label("max_version"),
            )
            .where(ProfileAssignment.device_id == device_id)
            .group_by(ProfileAssignment.profile_id)
            .subquery()
        )
        stmt = (
            select(ProfileAssignment)
            .join(
                subq,
                (ProfileAssignment.device_id == device_id)
                & (ProfileAssignment.profile_id == subq.c.profile_id)
                & (ProfileAssignment.profile_version == subq.c.max_version),
            )
            .order_by(ProfileAssignment.profile_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_assignment_by_version(
        self, profile_id: int, device_id: int, profile_version: int
    ) -> ProfileAssignment | None:
        stmt = select(ProfileAssignment).where(
            ProfileAssignment.profile_id == profile_id,
            ProfileAssignment.device_id == device_id,
            ProfileAssignment.profile_version == profile_version,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_assignment(self, data: AssignmentUpsert) -> ProfileAssignment:
        existing = await self.get_assignment_by_version(data.profile_id, data.device_id, data.profile_version)
        if existing:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(existing, key, value)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        instance = ProfileAssignment(**data.model_dump())
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def bulk_upsert_assignments(self, profile_id: int, assignments: list[AssignmentUpsert]) -> int:
        count = 0
        for data in assignments:
            existing = await self.get_assignment_by_version(data.profile_id, data.device_id, data.profile_version)
            if existing:
                for key, value in data.model_dump(exclude_unset=True).items():
                    setattr(existing, key, value)
            else:
                self.db.add(ProfileAssignment(**data.model_dump()))
            count += 1
        await self.db.commit()
        return count

    async def list_all_profiles(self) -> list[Profile]:
        stmt = select(Profile).order_by(Profile.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_affected_profiles_for_device(self, device_id: int) -> list[Profile]:
        device = await self.db.get(Device, device_id)
        if device is None:
            return []
        static_group_rows = await self.db.execute(
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
            else:
                for exclusion in scope.exclusions:
                    if exclusion.scope_type == ScopeType.SMART_GROUP:
                        affected.append(profile)
                        break
                    if (exclusion.scope_type == ScopeType.DEVICE and exclusion.exclude_id == device_id) or (
                        exclusion.scope_type == ScopeType.STATIC_GROUP and exclusion.exclude_id in static_group_ids
                    ):
                        affected.append(profile)
                        break
        return affected

    async def get_max_assignment_version(self, profile_id: int) -> int:
        stmt = select(func.coalesce(func.max(ProfileAssignment.profile_version), 0)).where(
            ProfileAssignment.profile_id == profile_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_assignment_device_ids_at_version(self, profile_id: int, version: int) -> set[int]:
        stmt = select(ProfileAssignment.device_id).where(
            ProfileAssignment.profile_id == profile_id,
            ProfileAssignment.profile_version == version,
        )
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all()}

    async def bulk_create_assignments(
        self,
        profile_id: int,
        version: int,
        device_ids: set[int],
        revoked_device_ids: set[int] | None = None,
    ) -> None:
        for device_id in device_ids:
            self.db.add(
                ProfileAssignment(
                    profile_id=profile_id,
                    device_id=device_id,
                    desired_state=AssignmentDesiredState.PRESENT,
                    status=AssignmentStatus.PENDING,
                    profile_version=version,
                )
            )
        for device_id in revoked_device_ids or set():
            self.db.add(
                ProfileAssignment(
                    profile_id=profile_id,
                    device_id=device_id,
                    desired_state=AssignmentDesiredState.ABSENT,
                    status=AssignmentStatus.REVOKE_PENDING,
                    profile_version=version,
                )
            )

    async def mark_assignment_sent(self, assignment_id: int, message_id: str) -> None:
        assignment = await self.db.get(ProfileAssignment, assignment_id)
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
        assignment = await self.db.get(ProfileAssignment, assignment_id)
        if assignment:
            assignment.status = AssignmentStatus.FAILED
            assignment.attempt_count += 1
            assignment.last_attempt_at = datetime.now(timezone.utc)
            assignment.last_error = error[:2000]
            await self.db.commit()


    async def remove_scope_references(self, scope_type: ScopeType, target_id: int) -> list[int]:
        """Remove all scope targets and exclusions matching the given type and ID from every profile.

        Returns the IDs of profiles whose scope was modified.
        """
        profiles = await self.list_all_profiles()
        affected: list[int] = []
        for profile in profiles:
            modified = False
            original_targets = list(profile.scope.targets)
            original_exclusions = list(profile.scope.exclusions)
            new_targets = [
                t for t in original_targets if not (t.scope_type == scope_type and (t.target_id or 0) == target_id)
            ]
            new_exclusions = [
                e for e in original_exclusions if not (e.scope_type == scope_type and (e.exclude_id or 0) == target_id)
            ]
            if len(new_targets) != len(original_targets):
                profile.scope.targets = new_targets
                modified = True
            if len(new_exclusions) != len(original_exclusions):
                profile.scope.exclusions = new_exclusions
                modified = True
            if modified:
                flag_modified(profile, "scope")
                affected.append(profile.id)
        if affected:
            await self.db.commit()
        return affected

