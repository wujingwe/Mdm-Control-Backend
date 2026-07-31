from app.domains.devices.models import Device
from app.domains.inventory_search.models import InventorySearch
from app.domains.inventory_search.repositories import InventorySearchRepository
from app.domains.inventory_search.schemas import (
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

    async def update_search(self, search_id: int, data: InventorySearchUpdate) -> int:
        return await self.repo.update(search_id, data)

    async def delete_search(self, search_id: int) -> int:
        return await self.repo.delete(search_id)

    async def execute_search(self, data: InventorySearchExecuteRequest) -> list[Device]:
        return await self.repo.search_devices(data.criteria)
