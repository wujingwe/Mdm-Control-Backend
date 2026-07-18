from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError
from app.devices.models import Device, DeviceExtensionAttribute
from app.devices.schemas import DeviceUpdate


class DeviceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Device]:
        stmt = select(Device).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> Device | None:
        stmt = (
            select(Device)
            .options(selectinload(Device.extension_attributes))
            .where(Device.id == record_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Device:
        instance = Device(**data)
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, record_id: int, data: DeviceUpdate) -> Device | None:
        values = data.model_dump(exclude_unset=True, exclude={"extension_attributes"})
        ext_attrs = data.extension_attributes

        if not values and ext_attrs is None:
            return await self.get_by_id(record_id)

        if values:
            stmt = update(Device).where(Device.id == record_id).values(**values)
            result = await self.db.execute(stmt)
            if result.rowcount == 0:  # type: ignore[attr-defined]
                return None
            self.db.expire(await self.db.get(Device, record_id))

        if ext_attrs is not None:
            await self.db.execute(
                delete(DeviceExtensionAttribute).where(
                    DeviceExtensionAttribute.device_id == record_id
                )
            )
            for attr in ext_attrs:
                self.db.add(
                    DeviceExtensionAttribute(
                        device_id=record_id,
                        extension_attribute_id=attr.extension_attribute_id,
                        extension_attribute_name=attr.extension_attribute_name,
                        value=attr.value,
                    )
                )
            self.db.expire(await self.db.get(Device, record_id))

        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err

        return await self.get_by_id(record_id)

    async def delete(self, record_id: int) -> bool:
        stmt = delete(Device).where(Device.id == record_id).returning(Device.id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Device)
        result = await self.db.execute(stmt)
        return result.scalar_one()
