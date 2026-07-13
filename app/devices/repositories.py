from typing import Any
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.devices.models import Device
from app.core.exceptions import ConflictError


class DeviceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Device]:
        stmt = select(Device).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> Device | None:
        stmt = select(Device).where(Device.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> Device:
        instance = Device(**data)
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return instance

    async def update(self, record_id: int, data: dict[str, Any]) -> Device | None:
        if not data:
            return await self.get_by_id(record_id)
        stmt = update(Device).where(Device.id == record_id).values(**data).returning(Device)
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return result.scalars().one_or_none()

    async def delete(self, record_id: int) -> bool:
        stmt = delete(Device).where(Device.id == record_id).returning(Device.id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Device)
        result = await self.db.execute(stmt)
        return result.scalar_one()
