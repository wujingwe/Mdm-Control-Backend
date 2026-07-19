from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.profiles.models import Profile, ProfileAssignment
from app.profiles.schemas import (
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

    async def create(self, data: ProfileCreate) -> Profile:
        instance = Profile(**data.model_dump())
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
        stmt = (
            update(Profile)
            .where(Profile.id == record_id)
            .values(**values)
            .returning(Profile)
        )
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Profile with this name already exists") from err
        return result.scalars().one_or_none()

    async def delete(self, record_id: int) -> bool:
        stmt = delete(Profile).where(Profile.id == record_id).returning(Profile.id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Profile)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_assignments(self, profile_id: int) -> list[ProfileAssignment]:
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

    async def get_assignment(
        self, profile_id: int, device_id: int
    ) -> ProfileAssignment | None:
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
        existing = await self.get_assignment_by_version(
            data.profile_id, data.device_id, data.profile_version
        )
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

    async def bulk_upsert_assignments(
        self, profile_id: int, assignments: list[AssignmentUpsert]
    ) -> int:
        count = 0
        for data in assignments:
            existing = await self.get_assignment_by_version(
                data.profile_id, data.device_id, data.profile_version
            )
            if existing:
                for key, value in data.model_dump(exclude_unset=True).items():
                    setattr(existing, key, value)
            else:
                self.db.add(ProfileAssignment(**data.model_dump()))
            count += 1
        await self.db.commit()
        return count

    async def delete_old_version_assignments(
        self, profile_id: int, current_version: int
    ) -> None:
        stmt = delete(ProfileAssignment).where(
            ProfileAssignment.profile_id == profile_id,
            ProfileAssignment.profile_version < current_version,
        )
        await self.db.execute(stmt)
        await self.db.commit()
