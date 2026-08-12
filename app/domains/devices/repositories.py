from sqlalchemy import select, func, delete, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infra.core.base import utcnow
from app.infra.core.exceptions import ConflictError
from app.infra.core.types import JsonValue
from app.domains.devices.enums import DeviceStatus
from app.domains.devices.models import Device, DeviceExtensionAttributeValue
from app.domains.devices.schemas import DeviceCreate, DevicePatch, DeviceUpdate
from app.domains.static_groups.models import StaticGroupDevice


class DeviceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, skip: int = 0, limit: int = 100) -> list[Device]:
        stmt = select(Device).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, device_id: int) -> Device | None:
        stmt = (
            select(Device)
            .options(
                selectinload(Device.extension_attribute_values),
                selectinload(Device.profiles),
                selectinload(Device.mobile_apps),
            )
            .where(Device.id == device_id)
        )
        result = await self._db.execute(stmt, execution_options={"populate_existing": True})
        return result.scalar_one_or_none()

    async def get_by_serial(self, serial_number: str) -> Device | None:
        stmt = select(Device).where(Device.serial_number == serial_number)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def _apply_values(self, device: Device, values: dict[str, JsonValue]) -> Device:
        for field_name, value in values.items():
            setattr(device, field_name, value)
        device.updated_at = utcnow()
        try:
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource update violates a constraint") from err
        return device

    async def update_loaded(self, device: Device, data: DevicePatch) -> Device:
        """Apply a patch to a device that has already been loaded in this session."""
        return await self._apply_values(device, data.model_dump(exclude_unset=True))

    async def upsert_by_serial(self, serial_number: str, data: DeviceCreate) -> tuple[Device, bool]:
        """Insert the device, or apply the payload to the existing row keyed by serial.

        Returns (device, created) where created is True on first enrollment.
        The serial_number unique constraint arbitrates the create/update boundary,
        making concurrent registrations of the same serial race-safe.
        """
        instance = Device(**data.model_dump(exclude_unset=True))
        instance.serial_number = serial_number
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
            return instance, True
        except IntegrityError as err:
            await self._db.rollback()
            device = await self.get_by_serial(serial_number)
            if device is None:
                raise ConflictError("Resource already exists") from err
            return await self._apply_values(device, data.model_dump(exclude_unset=True)), False

    async def create(self, data: DeviceCreate) -> Device:
        instance = Device(**data.model_dump(exclude_unset=True))
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, device_id: int, data: DeviceUpdate) -> int:
        ext_attrs = data.extension_attribute_values
        scalar_values = data.model_dump(
            exclude_unset=True,
            exclude={"extension_attribute_values"},
        )

        if not scalar_values and ext_attrs is None:
            return 0

        device = await self._db.get(Device, device_id, with_for_update=True)
        if not device:
            return 0

        for field_name, value in scalar_values.items():
            setattr(device, field_name, value)

        if ext_attrs is not None:
            stmt = delete(DeviceExtensionAttributeValue).where(DeviceExtensionAttributeValue.device_id == device_id)
            await self._db.execute(stmt)

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
                await self._db.execute(insert(DeviceExtensionAttributeValue), rows)

            # If child changes should affect the parent timestamp:
            device.updated_at = utcnow()

        try:
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource update violates a constraint") from err

        return 1

    async def delete(self, record_id: int) -> int:
        stmt = delete(Device).where(Device.id == record_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Device)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def list_enrolled_ids(self) -> set[int]:
        stmt = select(Device.id).where(Device.status == DeviceStatus.ENROLLED)
        result = await self._db.execute(stmt)
        return {row[0] for row in result.all()}

    async def list_enrolled_ids_by_serials(self, serial_numbers: set[str]) -> set[int]:
        if not serial_numbers:
            return set()
        stmt = select(Device.id).where(
            Device.serial_number.in_(serial_numbers),
            Device.status == DeviceStatus.ENROLLED,
        )
        result = await self._db.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_enrolled_id(self, device_id: int) -> int | None:
        stmt = select(Device.id).where(
            Device.id == device_id,
            Device.status == DeviceStatus.ENROLLED,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def resolve_device_ids(self, static_group_id: int) -> set[int]:
        stmt = select(StaticGroupDevice.device_serial_number).where(
            StaticGroupDevice.static_group_id == static_group_id
        )
        result = await self._db.execute(stmt)
        serial_numbers = {row[0] for row in result.all()}
        return await self.list_enrolled_ids_by_serials(serial_numbers)

    async def get_serial_map(self, device_ids: set[int]) -> dict[int, str]:
        if not device_ids:
            return {}
        stmt = select(Device.id, Device.serial_number).where(Device.id.in_(device_ids))
        result = await self._db.execute(stmt)
        return {row.id: row.serial_number for row in result.all()}

    async def get_serial_number(self, device_id: int) -> str | None:
        stmt = select(Device.serial_number).where(Device.id == device_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()
