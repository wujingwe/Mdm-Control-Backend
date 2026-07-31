from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.infra.criteria import build_device_query
from app.infra.criteria.schemas import Criteria
from app.domains.devices.models import Device
from app.domains.inventory_search.models import InventorySearch
from app.domains.inventory_search.schemas import InventorySearchCreate, InventorySearchUpdate


class InventorySearchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def search_devices(self, criteria: list[Criteria]) -> list[Device]:
        where = build_device_query(criteria)
        if where is not None:
            stmt = select(Device).where(where).order_by(Device.id)
        else:
            stmt = select(Device).order_by(Device.id)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def list(self, skip: int = 0, limit: int = 100) -> list[InventorySearch]:
        stmt = select(InventorySearch).order_by(InventorySearch.id).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, search_id: int) -> InventorySearch | None:
        stmt = select(InventorySearch).where(InventorySearch.id == search_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: InventorySearchCreate, created_by: int) -> InventorySearch:
        instance = InventorySearch(**data.model_dump(), created_by=created_by)
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, record_id: int, data: InventorySearchUpdate) -> int:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return 0
        stmt = update(InventorySearch).where(InventorySearch.id == record_id).values(**values)
        try:
            result = await self._db.execute(stmt)
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return result.rowcount  # type: ignore

    async def delete(self, record_id: int) -> int:
        stmt = delete(InventorySearch).where(InventorySearch.id == record_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        stmt = select(func.count()).select_from(InventorySearch)
        result = await self._db.execute(stmt)
        return result.scalar_one()
