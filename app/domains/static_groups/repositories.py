from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infra.core.exceptions import ConflictError
from app.domains.static_groups.models import StaticGroup, StaticGroupDevice
from app.domains.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate


class StaticGroupRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, skip: int = 0, limit: int = 100) -> list[StaticGroup]:
        stmt = (
            select(StaticGroup)
            .options(selectinload(StaticGroup.devices))
            .order_by(StaticGroup.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> StaticGroup | None:
        stmt = select(StaticGroup).options(selectinload(StaticGroup.devices)).where(StaticGroup.id == record_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: StaticGroupCreate, created_by: int) -> StaticGroup:
        instance = StaticGroup(
            name=data.name,
            description=data.description,
            created_by=created_by,
        )
        self._db.add(instance)
        try:
            await self._db.flush()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Static group name already exists") from err

        for serial in data.device_serial_numbers:
            self._db.add(
                StaticGroupDevice(
                    static_group_id=instance.id,
                    device_serial_number=serial,
                )
            )
        try:
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Invalid device or duplicate device in group") from err

        await self._db.refresh(instance, attribute_names=["devices"])
        return instance

    async def update(self, record_id: int, data: StaticGroupUpdate) -> int:
        affected = 0

        # 1. Update scalar fields
        values = data.model_dump(exclude_unset=True, exclude={"device_serial_numbers"})
        if values:
            stmt = update(StaticGroup).where(StaticGroup.id == record_id).values(**values)
            try:
                result = await self._db.execute(stmt)
            except IntegrityError as err:
                await self._db.rollback()
                raise ConflictError("Resource already exists") from err
            affected += result.rowcount  # type: ignore

        # 2. Replace device collection
        if data.device_serial_numbers is not None:
            existing = (
                (
                    await self._db.execute(
                        select(StaticGroupDevice).where(
                            StaticGroupDevice.static_group_id == record_id,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for obj in existing:
                await self._db.delete(obj)

            for serial in data.device_serial_numbers:
                self._db.add(
                    StaticGroupDevice(
                        static_group_id=record_id,
                        device_serial_number=serial,
                    )
                )
            affected += 1

        # 3. Commit
        if affected:
            try:
                await self._db.commit()
            except IntegrityError as err:
                await self._db.rollback()
                raise ConflictError("Resource already exists") from err
            instance = await self._db.get(StaticGroup, record_id)
            if instance is not None:
                self._db.expire(instance, ["devices"])

        return affected

    async def delete(self, record_id: int) -> int:
        stmt = delete(StaticGroup).where(StaticGroup.id == record_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        stmt = select(func.count()).select_from(StaticGroup)
        result = await self._db.execute(stmt)
        return result.scalar_one()
