from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models.device import Device
from app.core.exceptions import ConflictError


class DeviceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all_simple(self, skip: int = 0, limit: int = 100) -> list[Device]:
        stmt = select(Device).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Device]:
        stmt = select(Device).offset(skip).limit(limit).options(selectinload(Device.policies))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> Device | None:
        stmt = select(Device).where(Device.id == record_id).options(selectinload(Device.policies))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_serial(self, serial: str) -> Device | None:
        stmt = select(Device).where(Device.serial_number == serial).options(selectinload(Device.policies))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[int]) -> list[Device]:
        stmt = select(Device).where(Device.id.in_(ids)).order_by(Device.id).options(selectinload(Device.policies))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
        stmt = select(func.count()).select_from(Device)
        result = await self.db.execute(stmt)
        return result.scalar_one()
