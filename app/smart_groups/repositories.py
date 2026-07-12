from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.smart_groups.models import SmartGroup
from app.core.exceptions import ConflictError


class SmartGroupRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[SmartGroup]:
        stmt = select(SmartGroup).order_by(SmartGroup.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> SmartGroup | None:
        stmt = select(SmartGroup).where(SmartGroup.id == record_id).options(selectinload(SmartGroup.policies))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> SmartGroup:
        instance = SmartGroup(**data)
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return instance

    async def update(self, record_id: int, data: dict[str, Any]) -> SmartGroup | None:
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
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return instance

    async def delete(self, record_id: int) -> bool:
        instance = await self.get_by_id(record_id)
        if not instance:
            return False
        await self.db.delete(instance)
        await self.db.commit()
        return True

    async def count(self) -> int:
        stmt = select(func.count()).select_from(SmartGroup)
        result = await self.db.execute(stmt)
        return result.scalar_one()
