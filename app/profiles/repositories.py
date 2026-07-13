from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.common.enums import AssignmentSource
from app.profiles.models import Profile
from app.profiles.profile_scope import ProfileScope
from app.profiles.profile_assignment import ProfileAssignment
from app.core.exceptions import ConflictError


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

    async def create(self, data: dict[str, Any]) -> Profile:
        instance = Profile(**data)
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Profile with this name already exists") from err  # noqa: TRY003, EM101
        return instance

    async def update(self, record_id: int, data: dict[str, Any]) -> Profile | None:
        instance = await self.get_by_id(record_id)
        if not instance:
            return None
        for key, value in data.items():
            setattr(instance, key, value)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Profile with this name already exists") from err  # noqa: TRY003, EM101
        return instance

    async def delete(self, record_id: int) -> bool:
        instance = await self.get_by_id(record_id)
        if not instance:
            return False
        await self.db.delete(instance)
        await self.db.commit()
        return True

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Profile)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_scope(self, profile_id: int) -> list[ProfileScope]:
        stmt = select(ProfileScope).where(ProfileScope.profile_id == profile_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def set_scope(self, profile_id: int, targets: list[dict[str, Any]]) -> None:
        stmt = select(ProfileScope).where(ProfileScope.profile_id == profile_id)
        result = await self.db.execute(stmt)
        for existing in result.scalars().all():
            await self.db.delete(existing)
        for t in targets:
            self.db.add(ProfileScope(profile_id=profile_id, **t))
        await self.db.commit()

    async def get_assignments(self, profile_id: int) -> list[ProfileAssignment]:
        stmt = select(ProfileAssignment).where(ProfileAssignment.profile_id == profile_id).order_by(ProfileAssignment.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_assignment(self, profile_id: int, device_id: int) -> ProfileAssignment | None:
        stmt = select(ProfileAssignment).where(
            ProfileAssignment.profile_id == profile_id,
            ProfileAssignment.device_id == device_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_assignment(self, data: dict[str, Any]) -> ProfileAssignment:
        existing = await self.get_assignment(data["profile_id"], data["device_id"])
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        instance = ProfileAssignment(**data)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def delete_non_direct_assignments(self, profile_id: int) -> None:
        stmt = select(ProfileAssignment).where(
            ProfileAssignment.profile_id == profile_id,
            ProfileAssignment.source != AssignmentSource.DIRECT,
        )
        result = await self.db.execute(stmt)
        for assignment in result.scalars().all():
            await self.db.delete(assignment)
        await self.db.commit()
