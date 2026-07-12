from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.static_groups.models import StaticGroup
from app.static_groups.static_group_device import StaticGroupDevice
from app.core.exceptions import ConflictError


class StaticGroupRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[StaticGroup]:
        stmt = select(StaticGroup).order_by(StaticGroup.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> StaticGroup | None:
        stmt = select(StaticGroup).where(StaticGroup.id == record_id).options(selectinload(StaticGroup.policies))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict[str, Any]) -> StaticGroup:
        instance = StaticGroup(**data)
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return instance

    async def update(self, record_id: int, data: dict[str, Any]) -> StaticGroup | None:
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
        stmt = select(func.count()).select_from(StaticGroup)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_device_serial_numbers(self, group_id: int) -> list[str]:
        stmt = select(StaticGroupDevice.device_serial_number).where(
            StaticGroupDevice.static_group_id == group_id
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def set_device_serial_numbers(self, group_id: int, serial_numbers: list[str]) -> None:
        stmt = select(StaticGroupDevice).where(StaticGroupDevice.static_group_id == group_id)
        result = await self.db.execute(stmt)
        existing = list(result.scalars().all())
        for device in existing:
            await self.db.delete(device)
        for serial in serial_numbers:
            self.db.add(StaticGroupDevice(static_group_id=group_id, device_serial_number=serial))
        await self.db.commit()
