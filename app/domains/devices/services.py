from app.domains.devices.models import Device
from app.domains.devices.repositories import DeviceRepository
from app.domains.devices.schemas import DeviceUpdate
from app.domains.shared.reconciliation_service import ReconciliationService

RECONCILIATION_TRIGGER_FIELDS = frozenset(
    {
        "name",
        "serial_number",
        "os_version",
        "connection_status",
        "status",
        "battery_status",
        "total_storage",
        "available_storage",
        "total_memory",
        "available_memory",
        "extension_attribute_values",
    }
)


class DeviceService:
    def __init__(self, repo: DeviceRepository, reconciliation_service: ReconciliationService) -> None:
        self.repo = repo
        self.reconciliation_service = reconciliation_service

    async def list_devices(self, skip: int = 0, limit: int = 100) -> tuple[list[Device], int]:
        items = await self.repo.list(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_device(self, device_id: int) -> Device | None:
        return await self.repo.get_by_id(device_id)

    async def update_device(self, device_id: int, data: DeviceUpdate) -> int:
        updated = await self.repo.update(device_id, data)
        if updated and data.model_fields_set & RECONCILIATION_TRIGGER_FIELDS:
            await self.reconciliation_service.recalculate_profiles_for_device(device_id)
            await self.reconciliation_service.recalculate_mobile_apps_for_device(device_id)
        return updated
