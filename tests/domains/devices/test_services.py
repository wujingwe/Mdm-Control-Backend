from datetime import timezone
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.domains.commands.enums import CommandStatus
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.devices.schemas import (
    CommandReportIn,
    Certificate,
    DeviceRegisterRequest,
    DeviceReportIn,
    DeviceUpdate,
    Network,
    ProfileAssignmentReportIn,
    Wifi,
)
from app.domains.devices.services import DeviceService, _latest_certificate_expiry
from app.domains.mobile_apps.schemas import MobileAppAssignmentReportIn
from app.domains.profiles.enums import AssignmentStatus


class TestDeviceService:
    def test_latest_certificate_expiry_normalizes_timezones(self) -> None:
        result = _latest_certificate_expiry(
            [
                Certificate(expiry="2027-01-01T00:00:00"),
                Certificate(expiry="2026-12-31T20:00:00-05:00"),
            ]
        )
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.isoformat() == "2027-01-01T01:00:00+00:00"

    def test_latest_certificate_expiry_ignores_missing_and_invalid_values(self) -> None:
        assert _latest_certificate_expiry(None) is None
        assert _latest_certificate_expiry([Certificate(), Certificate(expiry="not-a-date")]) is None

    @pytest.fixture
    def repo(self) -> MagicMock:
        m = MagicMock()
        m.list = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        m.get_by_serial = AsyncMock(return_value=None)
        m.update = AsyncMock(return_value=None)
        m.db = AsyncMock()
        return m

    @pytest.fixture
    def command_repo(self) -> MagicMock:
        m = MagicMock()
        m.get_by_id = AsyncMock(return_value=None)
        m.update_status = AsyncMock()
        m.update_status_reports = AsyncMock()
        return m

    @pytest.fixture
    def profile_repo(self) -> MagicMock:
        m = MagicMock()
        m.get_assignment_by_id = AsyncMock(return_value=None)
        m.update_assignment_report = AsyncMock()
        m.update_assignment_reports = AsyncMock()
        return m

    @pytest.fixture
    def mobile_app_repo(self) -> MagicMock:
        m = MagicMock()
        m.get_assignment_by_id = AsyncMock(return_value=None)
        m.update_assignment_report = AsyncMock()
        m.update_assignment_reports = AsyncMock()
        return m

    @pytest.fixture
    def reconciliation_service(self) -> MagicMock:
        m = MagicMock()
        m.recalculate_profiles_for_device = AsyncMock()
        m.recalculate_mobile_apps_for_device = AsyncMock()
        return m

    @staticmethod
    def make_service(
        repo: MagicMock,
        reconciliation_service: MagicMock,
        command_repo: MagicMock,
        profile_repo: MagicMock | None = None,
        mobile_app_repo: MagicMock | None = None,
    ) -> DeviceService:
        return DeviceService(
            repo, reconciliation_service, command_repo, profile_repo or MagicMock(), mobile_app_repo or MagicMock()
        )

    async def test_list_devices(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        svc = self.make_service(repo, reconciliation_service, command_repo)
        items, total = await svc.list_devices()
        assert items == []
        assert total == 0
        repo.list.assert_called_once_with(skip=0, limit=100)
        repo.count.assert_called_once()

    async def test_list_devices_paginated(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        svc = self.make_service(repo, reconciliation_service, command_repo)
        await svc.list_devices(skip=10, limit=20)
        repo.list.assert_called_once_with(skip=10, limit=20)

    async def test_get_device_found(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        fake = MagicMock()
        repo.get_by_id = AsyncMock(return_value=fake)
        svc = self.make_service(repo, reconciliation_service, command_repo)
        result = await svc.get_device(1)
        assert result is fake
        repo.get_by_id.assert_called_once_with(1)

    async def test_get_device_not_found(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        svc = self.make_service(repo, reconciliation_service, command_repo)
        result = await svc.get_device(999)
        assert result is None

    async def test_get_auth_by_serial_not_found(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        svc = self.make_service(repo, reconciliation_service, command_repo)
        result = await svc.get_auth_by_serial("SN-MISSING")
        assert result is None

    async def test_get_auth_by_serial_returns_latest_certificate(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        device = MagicMock(
            serial_number="SN-AUTH",
            status=DeviceStatus.ENROLLED,
            certificates=[Certificate(expiry="2027-01-01T00:00:00Z"), Certificate(expiry="2026-01-01T00:00:00Z")],
        )
        repo.get_by_serial = AsyncMock(return_value=device)
        svc = self.make_service(repo, reconciliation_service, command_repo)
        result = await svc.get_auth_by_serial("SN-AUTH")
        assert result is not None
        assert result.serial_number == "SN-AUTH"
        assert result.enrolled is True
        assert result.cert_valid_until.isoformat() == "2027-01-01T00:00:00+00:00"

    async def test_get_auth_by_serial_rejects_device_without_valid_certificate(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        device = MagicMock(serial_number="SN-NOCERT", certificates=[Certificate(expiry="invalid")])
        repo.get_by_serial = AsyncMock(return_value=device)
        svc = self.make_service(repo, reconciliation_service, command_repo)
        with pytest.raises(HTTPException) as error:
            await svc.get_auth_by_serial("SN-NOCERT")
        assert error.value.status_code == 404
        assert error.value.detail == "No valid certificate found"

    async def test_update_device_triggers_reconciliation(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = self.make_service(repo, reconciliation_service, command_repo)
        data = DeviceUpdate(connection_status=ConnectionStatus.DISCONNECTED)
        result = await svc.update_device(1, data)
        assert result == 1
        repo.update.assert_called_once_with(1, data)
        reconciliation_service.recalculate_profiles_for_device.assert_awaited_once_with(1)
        reconciliation_service.recalculate_mobile_apps_for_device.assert_awaited_once_with(1)

    async def test_update_device_non_trigger_field_skips_reconciliation(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = self.make_service(repo, reconciliation_service, command_repo)
        data = DeviceUpdate(network=Network(wifi=Wifi(ssid="Guest")))
        result = await svc.update_device(1, data)
        assert result == 1
        reconciliation_service.recalculate_profiles_for_device.assert_not_called()
        reconciliation_service.recalculate_mobile_apps_for_device.assert_not_called()

    async def test_update_device_not_found(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=0)
        svc = self.make_service(repo, reconciliation_service, command_repo)
        result = await svc.update_device(999, DeviceUpdate(connection_status=ConnectionStatus.DISCONNECTED))
        assert result == 0
        repo.update.assert_called_once()
        reconciliation_service.recalculate_profiles_for_device.assert_not_called()

    async def test_register_upserts_and_reconciles_on_first_enrollment(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        device = MagicMock(id=1)
        repo.upsert_by_serial = AsyncMock(return_value=(device, True))
        svc = self.make_service(repo, reconciliation_service, command_repo)
        result = await svc.register("SN-1", DeviceRegisterRequest(name="Pixel", os_version="15.0"))
        assert result is device
        repo.upsert_by_serial.assert_awaited_once()
        args, _ = repo.upsert_by_serial.await_args
        assert args[0] == "SN-1"
        payload = args[1]
        assert payload.serial_number == "SN-1"
        assert payload.connection_status == ConnectionStatus.UNKNOWN
        assert payload.status == DeviceStatus.ENROLLED
        reconciliation_service.recalculate_profiles_for_device.assert_awaited_once_with(1)
        reconciliation_service.recalculate_mobile_apps_for_device.assert_awaited_once_with(1)

    async def test_register_upserts_and_reconciles_on_re_enrollment(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        device = MagicMock(id=1)
        repo.upsert_by_serial = AsyncMock(return_value=(device, False))
        svc = self.make_service(repo, reconciliation_service, command_repo)
        result = await svc.register("SN-1", DeviceRegisterRequest(name="Pixel", os_version="15.0"))
        assert result is device
        repo.upsert_by_serial.assert_awaited_once()
        reconciliation_service.recalculate_profiles_for_device.assert_awaited_once_with(1)
        reconciliation_service.recalculate_mobile_apps_for_device.assert_awaited_once_with(1)

    async def test_report_in_updates_profile_assignment_status(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock, profile_repo: MagicMock
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_loaded = AsyncMock(return_value=device)
        assignment = MagicMock(device_id=1)
        profile_repo.get_assignment_by_id = AsyncMock(return_value=assignment)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo)
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            profile_assignments=[
                ProfileAssignmentReportIn(
                    assignment_id=7,
                    status=AssignmentStatus.APPLIED,
                    result_message="Profile applied",
                ),
            ],
        )
        await svc.report_in("SN-1", data)
        profile_repo.update_assignment_reports.assert_awaited_once_with(
            1, {7: (AssignmentStatus.APPLIED, "Profile applied")}
        )

    async def test_report_in_ignores_assignment_for_other_device(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock, profile_repo: MagicMock
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_loaded = AsyncMock(return_value=device)
        assignment = MagicMock(device_id=99)
        profile_repo.get_assignment_by_id = AsyncMock(return_value=assignment)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo)
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            profile_assignments=[
                ProfileAssignmentReportIn(
                    assignment_id=7,
                    status=AssignmentStatus.APPLIED,
                ),
            ],
        )
        await svc.report_in("SN-1", data)
        profile_repo.update_assignment_reports.assert_awaited_once_with(1, {7: (AssignmentStatus.APPLIED, None)})

    async def test_report_in_ignores_unknown_assignment(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock, profile_repo: MagicMock
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_loaded = AsyncMock(return_value=device)
        profile_repo.get_assignment_by_id = AsyncMock(return_value=None)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo)
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            profile_assignments=[
                ProfileAssignmentReportIn(
                    assignment_id=7,
                    status=AssignmentStatus.APPLIED,
                ),
            ],
        )
        await svc.report_in("SN-1", data)
        profile_repo.update_assignment_reports.assert_awaited_once_with(1, {7: (AssignmentStatus.APPLIED, None)})

    async def test_report_in_updates_mobile_app_assignment_status(
        self,
        repo: MagicMock,
        reconciliation_service: MagicMock,
        command_repo: MagicMock,
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_loaded = AsyncMock(return_value=device)
        assignment = MagicMock(device_id=1)
        mobile_app_repo.get_assignment_by_id = AsyncMock(return_value=assignment)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo, mobile_app_repo)
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            mobile_app_assignments=[
                MobileAppAssignmentReportIn(
                    assignment_id=9,
                    status=AssignmentStatus.APPLIED,
                    result_message="App installed",
                ),
            ],
        )
        await svc.report_in("SN-1", data)
        mobile_app_repo.update_assignment_reports.assert_awaited_once_with(
            1, {9: (AssignmentStatus.APPLIED, "App installed")}
        )

    async def test_report_in_ignores_mobile_app_assignment_for_other_device(
        self,
        repo: MagicMock,
        reconciliation_service: MagicMock,
        command_repo: MagicMock,
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_loaded = AsyncMock(return_value=device)
        assignment = MagicMock(device_id=99)
        mobile_app_repo.get_assignment_by_id = AsyncMock(return_value=assignment)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo, mobile_app_repo)
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            mobile_app_assignments=[
                MobileAppAssignmentReportIn(
                    assignment_id=9,
                    status=AssignmentStatus.APPLIED,
                ),
            ],
        )
        await svc.report_in("SN-1", data)
        mobile_app_repo.update_assignment_reports.assert_awaited_once_with(1, {9: (AssignmentStatus.APPLIED, None)})

    async def test_report_in_ignores_unknown_mobile_app_assignment(
        self,
        repo: MagicMock,
        reconciliation_service: MagicMock,
        command_repo: MagicMock,
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_loaded = AsyncMock(return_value=device)
        mobile_app_repo.get_assignment_by_id = AsyncMock(return_value=None)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo, mobile_app_repo)
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            mobile_app_assignments=[
                MobileAppAssignmentReportIn(
                    assignment_id=9,
                    status=AssignmentStatus.APPLIED,
                ),
            ],
        )
        await svc.report_in("SN-1", data)
        mobile_app_repo.update_assignment_reports.assert_awaited_once_with(1, {9: (AssignmentStatus.APPLIED, None)})

    async def test_report_in_combined_command_and_assignments(
        self,
        repo: MagicMock,
        reconciliation_service: MagicMock,
        command_repo: MagicMock,
        profile_repo: MagicMock,
        mobile_app_repo: MagicMock,
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_loaded = AsyncMock(return_value=device)
        command_repo.get_by_id = AsyncMock(return_value=MagicMock(device_id=1))
        profile_repo.get_assignment_by_id = AsyncMock(return_value=MagicMock(device_id=1))
        mobile_app_repo.get_assignment_by_id = AsyncMock(return_value=MagicMock(device_id=1))
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo, mobile_app_repo)
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            commands=[
                CommandReportIn(
                    command_id=1,
                    status=CommandStatus.COMPLETED,
                ),
            ],
            profile_assignments=[
                ProfileAssignmentReportIn(
                    assignment_id=7,
                    status=AssignmentStatus.APPLIED,
                ),
            ],
            mobile_app_assignments=[
                MobileAppAssignmentReportIn(
                    assignment_id=9,
                    status=AssignmentStatus.APPLIED,
                ),
            ],
        )
        await svc.report_in("SN-1", data)
        command_repo.update_status_reports.assert_awaited_once_with(1, {1: (CommandStatus.COMPLETED, None)})
        profile_repo.update_assignment_reports.assert_awaited_once_with(1, {7: (AssignmentStatus.APPLIED, None)})
        mobile_app_repo.update_assignment_reports.assert_awaited_once_with(1, {9: (AssignmentStatus.APPLIED, None)})
        repo.get_by_serial.assert_awaited_once_with("SN-1")
        repo.update_loaded.assert_awaited_once_with(device, ANY)
