from datetime import datetime

from fastapi import HTTPException, status

from app.domains.commands.repositories import CommandRepository
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.devices.models import Device
from app.domains.devices.repositories import DeviceRepository
from app.domains.devices.schemas import DeviceAuthResponse, DeviceRegisterRequest, DeviceReportIn, DeviceUpdate
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.repositories import ProfileRepository
from app.domains.shared.reconciliation_service import ReconciliationService
from app.infra.core.base import utcnow

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
        cert_valid_until: datetime | None = None
        for certificate in device.certificates or []:
            if certificate.expiry:
                try:
                    parsed = datetime.fromisoformat(certificate.expiry.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if cert_valid_until is None or parsed > cert_valid_until:
                    cert_valid_until = parsed
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
            await self.reconciliation_service.recalculate_profiles_for_device(device_id)
            await self.reconciliation_service.recalculate_mobile_apps_for_device(device_id)
        return updated

    async def register(self, serial_number: str, data: DeviceRegisterRequest) -> Device:
        """Idempotently bind a device to the backend, keyed by serial."""
        existing = await self.repo.get_by_serial(serial_number)
        now = utcnow()
        if existing is None:
            return await self.repo.create(
                {
                    "name": data.name,
                    "serial_number": serial_number,
                    "os_version": data.os_version,
                    "connection_status": ConnectionStatus.UNKNOWN,
                    "status": DeviceStatus.ENROLLED,
                    "last_enrolled_at": now,
                    "certificates": data.certificates,
                }
            )
        device = await self.repo.update_by_serial(
            serial_number,
            {
                "name": data.name,
                "os_version": data.os_version,
                "status": DeviceStatus.ENROLLED,
                "last_enrolled_at": now,
                "certificates": data.certificates,
            },
        )
        assert device is not None
        await self.reconciliation_service.recalculate_profiles_for_device(device.id)
        await self.reconciliation_service.recalculate_mobile_apps_for_device(device.id)
        return device

    async def report_in(self, serial_number: str, data: DeviceReportIn) -> Device | None:
        """Record a device's report-in. The backend decides on unknown serials."""
        device = await self.repo.get_by_serial(serial_number)
        if device is None:
            return None
        for command in data.commands or []:
            record = await self.command_repo.get_by_id(command.command_id)
            if record is not None and record.device_id == device.id:
                await self.command_repo.update_status(command.command_id, command.status, command.result_message)
        for assignment in data.profile_assignments or []:
            assignment_record = await self.profile_repo.get_assignment_by_id(assignment.assignment_id)
            if assignment_record is not None and assignment_record.device_id == device.id:
                await self.profile_repo.update_assignment_report(
                    assignment.assignment_id, assignment.status, assignment.result_message
                )
        for app_assignment in data.mobile_app_assignments or []:
            mobile_assignment_record = await self.mobile_app_repo.get_assignment_by_id(app_assignment.assignment_id)
            if mobile_assignment_record is not None and mobile_assignment_record.device_id == device.id:
                await self.mobile_app_repo.update_assignment_report(
                    app_assignment.assignment_id, app_assignment.status, app_assignment.result_message
                )
        fields = data.model_dump(
            exclude_unset=True, exclude={"commands", "profile_assignments", "mobile_app_assignments"}
        )
        if not fields:
            return device
        updated = await self.repo.update_by_serial(serial_number, fields)
        assert updated is not None
        if data.model_fields_set & RECONCILIATION_TRIGGER_FIELDS:
            await self.reconciliation_service.recalculate_profiles_for_device(device.id)
            await self.reconciliation_service.recalculate_mobile_apps_for_device(device.id)
        return updated
