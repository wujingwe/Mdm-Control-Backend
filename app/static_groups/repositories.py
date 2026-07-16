from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.static_groups.models import StaticGroup, StaticGroupDevice
from app.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate
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

    async def create(self, data: StaticGroupCreate) -> StaticGroup:
        instance = StaticGroup(
            name=data.name,
            description=data.description,
            created_by=data.created_by,
        )
        self.db.add(instance)
        try:
            await self.db.flush()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101

        for serial in data.device_serial_numbers:
            self.db.add(StaticGroupDevice(
                static_group_id=instance.id,
                device_serial_number=serial,
            ))

        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def update(self, record_id: int, data: StaticGroupUpdate) -> StaticGroup | None:
        values = data.model_dump(exclude_unset=True)
        values.pop("device_serial_numbers", None)

        if values:
            stmt = (
                update(StaticGroup)
                .where(StaticGroup.id == record_id)
                .values(**values)
                .returning(StaticGroup)
            )
            await self.db.execute(stmt)
            try:
                await self.db.commit()
            except IntegrityError as err:
                await self.db.rollback()
                raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101

        if data.device_serial_numbers is not None:
            del_stmt = delete(StaticGroupDevice).where(
                StaticGroupDevice.static_group_id == record_id,
            )
            await self.db.execute(del_stmt)
            for serial in data.device_serial_numbers:
                self.db.add(StaticGroupDevice(
                    static_group_id=record_id,
                    device_serial_number=serial,
                ))
            await self.db.commit()

        return await self.get_by_id(record_id)

    async def delete(self, record_id: int) -> bool:
        stmt = delete(StaticGroup).where(StaticGroup.id == record_id).returning(StaticGroup.id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(StaticGroup)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_device_serial_numbers(self, group_id: int) -> list[str]:
        stmt = select(StaticGroupDevice.device_serial_number).where(
            StaticGroupDevice.static_group_id == group_id,
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
