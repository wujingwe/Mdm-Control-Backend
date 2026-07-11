from app.models.inventory_search import InventorySearch
from app.repositories.inventory_search import InventorySearchRepository


class InventorySearchService:
    def __init__(self, repo: InventorySearchRepository) -> None:
        self.repo = repo

    async def list_searches(self, skip: int = 0, limit: int = 100) -> tuple[list[InventorySearch], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_search(self, search_id: int) -> InventorySearch | None:
        return await self.repo.get_by_id(search_id)

    async def create_search(self, data: dict) -> InventorySearch:
        return await self.repo.create(data)

    async def update_search(self, search_id: int, data: dict) -> InventorySearch | None:
        return await self.repo.update(search_id, data)

    async def delete_search(self, search_id: int) -> bool:
        return await self.repo.delete(search_id)
