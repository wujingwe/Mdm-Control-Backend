from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError
from app.static_groups.models import StaticGroup, StaticGroupDevice
from app.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate


class StaticGroupRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[StaticGroup]:
        stmt = (
            select(StaticGroup)
            .options(selectinload(StaticGroup.devices))
            .order_by(StaticGroup.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> StaticGroup | None:
        stmt = (
            select(StaticGroup)
            .options(selectinload(StaticGroup.devices))
            .where(StaticGroup.id == record_id)
        )
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
            self.db.add(
                StaticGroupDevice(
                    static_group_id=instance.id,
                    device_serial_number=serial,
                )
            )

        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        group_id = instance.id
        self.db.expire(instance)
        return await self.get_by_id(group_id)

    async def update(
        self, record_id: int, data: StaticGroupUpdate
    ) -> StaticGroup | None:
        has_changes = False

        # 1. Update scalar fields
        values = data.model_dump(exclude_unset=True, exclude={"device_serial_numbers"})
        if values:
            stmt = (
                update(StaticGroup).where(StaticGroup.id == record_id).values(**values)
            )
            try:
                await self.db.execute(stmt)
            except IntegrityError as err:
                await self.db.rollback()
                raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
            has_changes = True

        # 2. Replace device collection
        if data.device_serial_numbers is not None:
            existing = (
                (
                    await self.db.execute(
                        select(StaticGroupDevice).where(
                            StaticGroupDevice.static_group_id == record_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for obj in existing:
                await self.db.delete(obj)

            for serial in data.device_serial_numbers:
                self.db.add(
                    StaticGroupDevice(
                        static_group_id=record_id,
                        device_serial_number=serial,
                    )
                )
            has_changes = True

        # 3. Commit and return fresh state
        if has_changes:
            try:
                await self.db.commit()
            except IntegrityError as err:
                await self.db.rollback()
                raise ConflictError("Resource already exists") from err
            instance = await self.db.get(StaticGroup, record_id)
            if instance is not None:
                self.db.expire(instance)

        return await self.get_by_id(record_id)

    async def delete(self, record_id: int) -> bool:
        stmt = (
            delete(StaticGroup)
            .where(StaticGroup.id == record_id)
            .returning(StaticGroup.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(StaticGroup)
        result = await self.db.execute(stmt)
        return result.scalar_one()
