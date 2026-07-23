from app.extension_attributes.models import ExtensionAttribute
from app.extension_attributes.repositories import ExtensionAttributeRepository
from app.extension_attributes.schemas import (
    ExtensionAttributeCreate,
    ExtensionAttributeUpdate,
)


class ExtensionAttributeService:
    def __init__(self, repo: ExtensionAttributeRepository) -> None:
        self.repo = repo

    async def list_attributes(self, skip: int = 0, limit: int = 100) -> tuple[list[ExtensionAttribute], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_attribute(self, attribute_id: int) -> ExtensionAttribute | None:
        return await self.repo.get_by_id(attribute_id)

    async def create_attribute(self, data: ExtensionAttributeCreate) -> ExtensionAttribute:
        return await self.repo.create(data)

    async def update_attribute(self, attribute_id: int, data: ExtensionAttributeUpdate) -> ExtensionAttribute | None:
        return await self.repo.update(attribute_id, data)

    async def delete_attribute(self, attribute_id: int) -> bool:
        return await self.repo.delete(attribute_id)
