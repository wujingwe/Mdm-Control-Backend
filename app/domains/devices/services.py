from app.domains.devices.models import Device
from app.domains.devices.repositories import DeviceRepository
from app.domains.devices.schemas import DeviceUpdate


class DeviceService:
    def __init__(self, repo: DeviceRepository) -> None:
        self.repo = repo

    async def list_devices(self, skip: int = 0, limit: int = 100) -> tuple[list[Device], int]:
        items = await self.repo.list(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_device(self, device_id: int) -> Device | None:
        return await self.repo.get_by_id(device_id)

    async def update_device(self, device_id: int, data: DeviceUpdate) -> Device | None:
        device = await self.repo.get_by_id(device_id)
        if not device:
            return None
        return await self.repo.update(device_id, data)
