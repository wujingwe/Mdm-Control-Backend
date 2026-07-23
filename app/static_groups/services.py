from app.static_groups.models import StaticGroup
from app.static_groups.repositories import StaticGroupRepository
from app.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate


class StaticGroupService:
    def __init__(self, repo: StaticGroupRepository) -> None:
        self.repo = repo

    async def list_groups(self, skip: int = 0, limit: int = 100) -> tuple[list[StaticGroup], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_group(self, group_id: int) -> StaticGroup | None:
        return await self.repo.get_by_id(group_id)

    async def create_group(self, data: StaticGroupCreate) -> StaticGroup | None:
        return await self.repo.create(data)

    async def update_group(self, group_id: int, data: StaticGroupUpdate) -> StaticGroup | None:
        return await self.repo.update(group_id, data)

    async def delete_group(self, group_id: int) -> bool:
        return await self.repo.delete(group_id)
