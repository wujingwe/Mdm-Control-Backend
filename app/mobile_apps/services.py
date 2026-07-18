from app.mobile_apps.models import MobileApp
from app.mobile_apps.repositories import MobileAppRepository
from app.mobile_apps.schemas import MobileAppCreate, MobileAppUpdate


class MobileAppService:
    def __init__(self, repo: MobileAppRepository) -> None:
        self.repo = repo

    async def list_mobile_apps(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[MobileApp], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_mobile_app(self, mobile_app_id: int) -> MobileApp | None:
        return await self.repo.get_by_id(mobile_app_id)

    async def create_mobile_app(self, data: MobileAppCreate) -> MobileApp:
        return await self.repo.create(data)

    async def update_mobile_app(
        self, mobile_app_id: int, data: MobileAppUpdate
    ) -> MobileApp | None:
        return await self.repo.update(mobile_app_id, data)

    async def delete_mobile_app(self, mobile_app_id: int) -> bool:
        return await self.repo.delete(mobile_app_id)
