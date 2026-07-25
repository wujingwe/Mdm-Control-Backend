from sqlalchemy import select, func, delete, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.base import utcnow
from app.core.exceptions import ConflictError
from app.devices.models import Device, DeviceExtensionAttributeValue
from app.devices.schemas import DeviceUpdate


class DeviceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, skip: int = 0, limit: int = 100) -> list[Device]:
        stmt = select(Device).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, device_id: int) -> Device | None:
        stmt = select(Device).options(selectinload(Device.extension_attribute_values)).where(Device.id == device_id)
        result = await self.db.execute(stmt, execution_options={"populate_existing": True})
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

    async def update(self, device_id: int, data: DeviceUpdate) -> Device | None:
        ext_attrs = data.extension_attribute_values
        scalar_values = data.model_dump(
            exclude_unset=True,
            exclude={"extension_attribute_values"},
        )

        if not scalar_values and ext_attrs is None:
            return await self.get_by_id(device_id)

        device = await self.db.get(Device, device_id, with_for_update=True)
        if not device:
            return None

        for field_name, value in scalar_values.items():
            setattr(device, field_name, value)

        if ext_attrs is not None:
            stmt = delete(DeviceExtensionAttributeValue).where(DeviceExtensionAttributeValue.device_id == device_id)
            await self.db.execute(stmt)

            if ext_attrs:
                rows = [
                    {
                        "device_id": device_id,
                        "extension_attribute_id": attr.extension_attribute_id,
                        "extension_attribute_name": attr.extension_attribute_name,
                        "value": attr.value,
                    }
                    for attr in ext_attrs
                ]
                await self.db.execute(insert(DeviceExtensionAttributeValue), rows)

            # If child changes should affect the parent timestamp:
            device.updated_at = utcnow()

        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource update violates a constraint") from err

        return await self.get_by_id(device_id)

    async def delete(self, record_id: int) -> bool:
        stmt = delete(Device).where(Device.id == record_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Device)
        result = await self.db.execute(stmt)
        return result.scalar_one()
