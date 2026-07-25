from sqlalchemy import select

from app.criteria import build_device_query
from app.devices.models import Device
from app.inventory_search.models import InventorySearch
from app.inventory_search.repositories import InventorySearchRepository
from app.inventory_search.schemas import (
    InventorySearchCreate,
    InventorySearchExecuteRequest,
    InventorySearchUpdate,
)


class InventorySearchService:
    def __init__(self, repo: InventorySearchRepository) -> None:
        self.repo = repo

    async def list_searches(self, skip: int = 0, limit: int = 100) -> tuple[list[InventorySearch], int]:
        items = await self.repo.list(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_search(self, search_id: int) -> InventorySearch | None:
        return await self.repo.get_by_id(search_id)

    async def create_search(self, data: InventorySearchCreate, create_by: int) -> InventorySearch:
        return await self.repo.create(data, create_by)

    async def update_search(self, search_id: int, data: InventorySearchUpdate) -> InventorySearch | None:
        return await self.repo.update(search_id, data)

    async def delete_search(self, search_id: int) -> bool:
        return await self.repo.delete(search_id)

    async def execute_search(self, data: InventorySearchExecuteRequest) -> list[Device]:
        where = build_device_query(data.criteria)

        if where is not None:
            stmt = select(Device).where(where).order_by(Device.id)
        else:
            stmt = select(Device).order_by(Device.id)

        result = await self.repo.db.execute(stmt)
        return list(result.scalars().all())
