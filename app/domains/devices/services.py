from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.domains.commands.repositories import CommandRepository
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.devices.models import Device
from app.domains.devices.repositories import DeviceRepository
from app.domains.devices.schemas import (
    Certificate,
    DeviceAuthResponse,
    DeviceCreate,
    DevicePatch,
    DeviceRegisterRequest,
    DeviceReportIn,
    DeviceUpdate,
)
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.repositories import ProfileRepository
from app.domains.shared.reconciliation_service import ReconciliationService
from app.infra.core.base import utcnow

RECONCILIATION_TRIGGER_FIELDS = frozenset(
    {
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


def _latest_certificate_expiry(certificates: list[Certificate] | None) -> datetime | None:
    latest: datetime | None = None
    for certificate in certificates or []:
        if not certificate.expiry:
            continue
        try:
            parsed = datetime.fromisoformat(certificate.expiry.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        if latest is None or parsed > latest:
            latest = parsed
    return latest


class DeviceService:
    def __init__(
        self,
        repo: DeviceRepository,
        reconciliation_service: ReconciliationService,
        command_repo: CommandRepository,
        profile_repo: ProfileRepository,
        mobile_app_repo: MobileAppRepository,
    ) -> None:
        self.repo = repo
        self.reconciliation_service = reconciliation_service
        self.command_repo = command_repo
        self.profile_repo = profile_repo
        self.mobile_app_repo = mobile_app_repo

    async def list_devices(self, skip: int = 0, limit: int = 100) -> tuple[list[Device], int]:
        items = await self.repo.list(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_device(self, device_id: int) -> Device | None:
        return await self.repo.get_by_id(device_id)

    async def get_auth_by_serial(self, serial_number: str) -> DeviceAuthResponse | None:
        device = await self.repo.get_by_serial(serial_number)
        if device is None:
            return None
        cert_valid_until = _latest_certificate_expiry(device.certificates)
        if cert_valid_until is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No valid certificate found")
        return DeviceAuthResponse(
            serial_number=device.serial_number,
            enrolled=device.status == DeviceStatus.ENROLLED,
            cert_valid_until=cert_valid_until,
        )

    async def update_device(self, device_id: int, data: DeviceUpdate) -> int:
        updated = await self.repo.update(device_id, data)
        if updated and data.model_fields_set & RECONCILIATION_TRIGGER_FIELDS:
            await self._reconcile_device(device_id)
        return updated

    async def _reconcile_device(self, device_id: int) -> None:
        await self.reconciliation_service.recalculate_profiles_for_device(device_id)
        await self.reconciliation_service.recalculate_mobile_apps_for_device(device_id)

    async def register(self, serial_number: str, data: DeviceRegisterRequest) -> Device:
        """Idempotently bind a device to the backend, keyed by serial."""
        now = utcnow()
        device, _ = await self.repo.upsert_by_serial(
            serial_number,
            DeviceCreate(
                name=data.name,
                serial_number=serial_number,
                os_version=data.os_version,
                connection_status=ConnectionStatus.UNKNOWN,
                status=DeviceStatus.ENROLLED,
                last_enrolled_at=now,
                certificates=data.certificates,
            ),
        )
        await self._reconcile_device(device.id)
        return device

    async def report_in(self, serial_number: str, data: DeviceReportIn) -> Device | None:
        """Record a device's report-in. The backend decides on unknown serials."""
        device = await self.repo.get_by_serial(serial_number)
        if device is None:
            return None
        if data.commands:
            await self.command_repo.update_status_reports(
                device.id,
                {item.command_id: (item.status, item.result_message) for item in data.commands},
            )
        if data.profile_assignments:
            await self.profile_repo.update_assignment_reports(
                device.id,
                {item.assignment_id: (item.status, item.result_message) for item in data.profile_assignments},
            )
        if data.mobile_app_assignments:
            await self.mobile_app_repo.update_assignment_reports(
                device.id,
                {item.assignment_id: (item.status, item.result_message) for item in data.mobile_app_assignments},
            )
        fields = data.model_dump(
            exclude_unset=True, exclude={"commands", "profile_assignments", "mobile_app_assignments"}
        )
        if not fields:
            return device
        updated = await self.repo.update_loaded(device, DevicePatch(**fields))
        if data.model_fields_set & RECONCILIATION_TRIGGER_FIELDS:
            await self._reconcile_device(device.id)
        return updated
