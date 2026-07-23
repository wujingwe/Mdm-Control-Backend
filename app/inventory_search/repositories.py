from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.inventory_search.models import InventorySearch
from app.inventory_search.schemas import InventorySearchCreate, InventorySearchUpdate


class InventorySearchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[InventorySearch]:
        stmt = select(InventorySearch).order_by(InventorySearch.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> InventorySearch | None:
        stmt = select(InventorySearch).where(InventorySearch.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: InventorySearchCreate) -> InventorySearch:
        instance = InventorySearch(**data.model_dump())
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, record_id: int, data: InventorySearchUpdate) -> InventorySearch | None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_by_id(record_id)
        stmt = update(InventorySearch).where(InventorySearch.id == record_id).values(**values)
        await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return await self.get_by_id(record_id)

    async def delete(self, record_id: int) -> bool:
        stmt = delete(InventorySearch).where(InventorySearch.id == record_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    async def count(self) -> int:
        stmt = select(func.count()).select_from(InventorySearch)
        result = await self.db.execute(stmt)
        return result.scalar_one()
