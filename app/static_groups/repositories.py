from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.devices.models import Device
from app.static_groups.models import StaticGroup
from app.static_groups.static_group_device import StaticGroupDevice
from app.static_groups.schemas import StaticGroupCreateDB, StaticGroupUpdate
from app.core.exceptions import ConflictError


class StaticGroupRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[StaticGroup]:
        stmt = select(StaticGroup).order_by(StaticGroup.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> StaticGroup | None:
        stmt = select(StaticGroup).where(StaticGroup.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: StaticGroupCreateDB) -> StaticGroup:
        instance = StaticGroup(**data.model_dump())
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return instance

    async def update(self, record_id: int, data: StaticGroupUpdate) -> StaticGroup | None:
        values = data.model_dump(exclude_unset=True)
        values.pop("device_serial_numbers", None)
        if not values:
            return await self.get_by_id(record_id)
        stmt = update(StaticGroup).where(StaticGroup.id == record_id).values(**values).returning(StaticGroup)
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return result.scalars().one_or_none()

    async def delete(self, record_id: int) -> bool:
        stmt = delete(StaticGroup).where(StaticGroup.id == record_id).returning(StaticGroup.id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(StaticGroup)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_device_ids(self, group_id: int) -> list[int]:
        stmt = select(StaticGroupDevice.device_id).where(
            StaticGroupDevice.static_group_id == group_id
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_device_serial_numbers(self, group_id: int) -> list[str]:
        device_ids = await self.get_device_ids(group_id)
        if not device_ids:
            return []
        stmt = select(Device.serial_number).where(Device.id.in_(device_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def set_device_serial_numbers(self, group_id: int, serial_numbers: list[str]) -> None:
        stmt = select(StaticGroupDevice).where(StaticGroupDevice.static_group_id == group_id)
        result = await self.db.execute(stmt)
        existing = list(result.scalars().all())
        for device in existing:
            await self.db.delete(device)
        if serial_numbers:
            dev_stmt = select(Device.id).where(Device.serial_number.in_(serial_numbers))
            dev_result = await self.db.execute(dev_stmt)
            device_ids = list(dev_result.scalars().all())
            for dev_id in device_ids:
                self.db.add(StaticGroupDevice(static_group_id=group_id, device_id=dev_id))
        await self.db.commit()
