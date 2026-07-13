from app.static_groups.models import StaticGroup
from app.static_groups.repositories import StaticGroupRepository
from app.static_groups.schemas import StaticGroupCreate, StaticGroupCreateDB, StaticGroupUpdate


class StaticGroupService:
    def __init__(self, repo: StaticGroupRepository) -> None:
        self.repo = repo

    async def list_groups(self, skip: int = 0, limit: int = 100) -> list[StaticGroup]:
        return await self.repo.list_all(skip=skip, limit=limit)

    async def get_group(self, group_id: int) -> StaticGroup | None:
        return await self.repo.get_by_id(group_id)

    async def create_group(self, data: StaticGroupCreate) -> StaticGroup:
        serial_numbers = data.device_serial_numbers
        db_data = StaticGroupCreateDB(
            name=data.name,
            description=data.description,
            created_by=data.created_by,
        )
        group = await self.repo.create(db_data)
        if serial_numbers:
            await self.repo.set_device_serial_numbers(group.id, serial_numbers)
        return group

    async def update_group(self, group_id: int, data: StaticGroupUpdate) -> StaticGroup | None:
        return await self.repo.update(group_id, data)

    async def delete_group(self, group_id: int) -> bool:
        return await self.repo.delete(group_id)

    async def get_device_serial_numbers(self, group_id: int) -> list[str]:
        return await self.repo.get_device_serial_numbers(group_id)

    async def set_device_serial_numbers(self, group_id: int, serial_numbers: list[str]) -> None:
        await self.repo.set_device_serial_numbers(group_id, serial_numbers)
