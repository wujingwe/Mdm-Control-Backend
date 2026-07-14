from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.common.enums import AssignmentSource
from app.profiles.models import Profile
from app.profiles.models import ProfileScope
from app.profiles.models import ProfileAssignment
from app.profiles.schemas import ProfileCreate, ProfileUpdate, ScopeTarget, AssignmentUpsert
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

    async def create(self, data: ProfileCreate) -> Profile:
        instance = Profile(**data.model_dump())
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Profile with this name already exists") from err  # noqa: TRY003, EM101
        return instance

    async def update(self, record_id: int, data: ProfileUpdate) -> Profile | None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_by_id(record_id)
        stmt = update(Profile).where(Profile.id == record_id).values(**values).returning(Profile)
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Profile with this name already exists") from err  # noqa: TRY003, EM101
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

    async def get_scope(self, profile_id: int) -> list[ProfileScope]:
        stmt = select(ProfileScope).where(ProfileScope.profile_id == profile_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def set_scope(self, profile_id: int, targets: list[ScopeTarget]) -> None:
        stmt = select(ProfileScope).where(ProfileScope.profile_id == profile_id)
        result = await self.db.execute(stmt)
        for existing in result.scalars().all():
            await self.db.delete(existing)
        for t in targets:
            self.db.add(ProfileScope(profile_id=profile_id, target_type=t.target_type, target_id=t.target_id))
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

    async def upsert_assignment(self, data: AssignmentUpsert) -> ProfileAssignment:
        existing = await self.get_assignment(data.profile_id, data.device_id)
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

    async def delete_non_direct_assignments(self, profile_id: int) -> None:
        stmt = select(ProfileAssignment).where(
            ProfileAssignment.profile_id == profile_id,
            ProfileAssignment.source != AssignmentSource.DIRECT,
        )
        result = await self.db.execute(stmt)
        for assignment in result.scalars().all():
            await self.db.delete(assignment)
        await self.db.commit()
