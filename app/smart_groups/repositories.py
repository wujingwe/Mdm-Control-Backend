from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.smart_groups.models import SmartGroup
from app.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate


class SmartGroupRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[SmartGroup]:
        stmt = select(SmartGroup).order_by(SmartGroup.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> SmartGroup | None:
        stmt = select(SmartGroup).where(SmartGroup.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: SmartGroupCreate) -> SmartGroup:
        instance = SmartGroup(**data.model_dump())
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, record_id: int, data: SmartGroupUpdate) -> SmartGroup | None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_by_id(record_id)
        stmt = (
            update(SmartGroup)
            .where(SmartGroup.id == record_id)
            .values(**values)
            .returning(SmartGroup)
        )
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return result.scalars().one_or_none()

    async def delete(self, record_id: int) -> bool:
        stmt = (
            delete(SmartGroup)
            .where(SmartGroup.id == record_id)
            .returning(SmartGroup.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(SmartGroup)
        result = await self.db.execute(stmt)
        return result.scalar_one()
