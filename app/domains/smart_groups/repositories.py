from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.domains.devices.enums import DeviceStatus
from app.domains.devices.models import Device
from app.domains.smart_groups.models import SmartGroup
from app.domains.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate
from app.infra.criteria import build_device_query
from app.infra.criteria.schemas import Criteria


class SmartGroupRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, skip: int = 0, limit: int = 100) -> list[SmartGroup]:
        stmt = select(SmartGroup).order_by(SmartGroup.id).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> SmartGroup | None:
        stmt = select(SmartGroup).where(SmartGroup.id == record_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: SmartGroupCreate, created_by: int) -> SmartGroup:
        instance = SmartGroup(**data.model_dump(), created_by=created_by)
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, record_id: int, data: SmartGroupUpdate) -> int:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return 0
        stmt = update(SmartGroup).where(SmartGroup.id == record_id).values(**values)
        try:
            result = await self._db.execute(stmt)
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return result.rowcount  # type: ignore

    async def delete(self, record_id: int) -> int:
        stmt = delete(SmartGroup).where(SmartGroup.id == record_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        stmt = select(func.count()).select_from(SmartGroup)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def resolve_device_ids(self, smart_group_id: int) -> set[int]:
        group = await self.get_by_id(smart_group_id)
        if not group or not isinstance(group.criteria, list):
            return set()

        criteria = [Criteria.model_validate(item) for item in group.criteria]
        where = build_device_query(criteria)
        stmt = select(Device.id).where(Device.status == DeviceStatus.ENROLLED)
        if where is not None:
            stmt = stmt.where(where)
        result = await self._db.execute(stmt)
        return {row[0] for row in result.all()}
