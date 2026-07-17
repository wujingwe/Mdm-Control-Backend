from app.smart_groups.models import SmartGroup
from app.smart_groups.repositories import SmartGroupRepository
from app.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate


class SmartGroupService:
    def __init__(self, repo: SmartGroupRepository) -> None:
        self.repo = repo

    async def list_groups(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[SmartGroup], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_group(self, group_id: int) -> SmartGroup | None:
        return await self.repo.get_by_id(group_id)

    async def create_group(self, data: SmartGroupCreate) -> SmartGroup:
        return await self.repo.create(data)

    async def update_group(
        self, group_id: int, data: SmartGroupUpdate
    ) -> SmartGroup | None:
        return await self.repo.update(group_id, data)

    async def delete_group(self, group_id: int) -> bool:
        return await self.repo.delete(group_id)
