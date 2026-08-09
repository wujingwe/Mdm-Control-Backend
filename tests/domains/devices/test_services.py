from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domains.devices.schemas import DeviceReportIn, DeviceUpdate
from app.domains.devices.services import DeviceService
from app.domains.profiles.enums import AssignmentStatus


class TestDeviceService:
    @pytest.fixture
    def repo(self) -> MagicMock:
        m = MagicMock()
        m.list = AsyncMock(return_value=[])
        m.count = AsyncMock(return_value=0)
        m.get_by_id = AsyncMock(return_value=None)
        m.update = AsyncMock(return_value=None)
        m.db = AsyncMock()
        return m

    @pytest.fixture
    def command_repo(self) -> MagicMock:
        m = MagicMock()
        m.get_by_id = AsyncMock(return_value=None)
        m.update_status = AsyncMock()
        return m

    @pytest.fixture
    def profile_repo(self) -> MagicMock:
        m = MagicMock()
        m.get_assignment_by_id = AsyncMock(return_value=None)
        m.update_assignment_report = AsyncMock()
        return m

    @pytest.fixture
    def mobile_app_repo(self) -> MagicMock:
        m = MagicMock()
        m.get_assignment_by_id = AsyncMock(return_value=None)
        m.update_assignment_report = AsyncMock()
        return m

    @pytest.fixture
    def reconciliation_service(self) -> MagicMock:
        m = MagicMock()
        m.recalculate_profiles_for_device = AsyncMock()
        m.recalculate_mobile_apps_for_device = AsyncMock()
        return m

    def make_service(
        self,
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

    async def test_update_device_triggers_reconciliation(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=1)
        svc = self.make_service(repo, reconciliation_service, command_repo)
        data = DeviceUpdate(connection_status="Disconnected")
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
        data = DeviceUpdate(network={"wifi": {"ssid": "Guest"}})
        result = await svc.update_device(1, data)
        assert result == 1
        reconciliation_service.recalculate_profiles_for_device.assert_not_called()
        reconciliation_service.recalculate_mobile_apps_for_device.assert_not_called()

    async def test_update_device_not_found(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock
    ) -> None:
        repo.update = AsyncMock(return_value=0)
        svc = self.make_service(repo, reconciliation_service, command_repo)
        result = await svc.update_device(999, DeviceUpdate(connection_status="Disconnected"))
        assert result == 0
        repo.update.assert_called_once()
        reconciliation_service.recalculate_profiles_for_device.assert_not_called()

    async def test_report_in_updates_profile_assignment_status(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock, profile_repo: MagicMock
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_by_serial = AsyncMock(return_value=device)
        assignment = MagicMock(device_id=1)
        profile_repo.get_assignment_by_id = AsyncMock(return_value=assignment)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo)
        data = DeviceReportIn(
            connection_status="Connected",
            status="Enrolled",
            profile_assignments=[
                {
                    "assignment_id": 7,
                    "status": "APPLIED",
                    "result_message": "Profile applied",
                }
            ],
        )
        await svc.report_in("SN-1", data)
        profile_repo.update_assignment_report.assert_awaited_once_with(7, AssignmentStatus.APPLIED, "Profile applied")

    async def test_report_in_ignores_assignment_for_other_device(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock, profile_repo: MagicMock
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_by_serial = AsyncMock(return_value=device)
        assignment = MagicMock(device_id=99)
        profile_repo.get_assignment_by_id = AsyncMock(return_value=assignment)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo)
        data = DeviceReportIn(
            connection_status="Connected",
            status="Enrolled",
            profile_assignments=[{"assignment_id": 7, "status": "APPLIED"}],
        )
        await svc.report_in("SN-1", data)
        profile_repo.update_assignment_report.assert_not_called()

    async def test_report_in_ignores_unknown_assignment(
        self, repo: MagicMock, reconciliation_service: MagicMock, command_repo: MagicMock, profile_repo: MagicMock
    ) -> None:
        device = MagicMock(id=1)
        repo.get_by_serial = AsyncMock(return_value=device)
        repo.update_by_serial = AsyncMock(return_value=device)
        profile_repo.get_assignment_by_id = AsyncMock(return_value=None)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo)
        data = DeviceReportIn(
            connection_status="Connected",
            status="Enrolled",
            profile_assignments=[{"assignment_id": 7, "status": "APPLIED"}],
        )
        await svc.report_in("SN-1", data)
        profile_repo.update_assignment_report.assert_not_called()

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
        repo.update_by_serial = AsyncMock(return_value=device)
        assignment = MagicMock(device_id=1)
        mobile_app_repo.get_assignment_by_id = AsyncMock(return_value=assignment)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo, mobile_app_repo)
        data = DeviceReportIn(
            connection_status="Connected",
            status="Enrolled",
            mobile_app_assignments=[
                {
                    "assignment_id": 9,
                    "status": "APPLIED",
                    "result_message": "App installed",
                }
            ],
        )
        await svc.report_in("SN-1", data)
        mobile_app_repo.update_assignment_report.assert_awaited_once_with(9, AssignmentStatus.APPLIED, "App installed")

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
        repo.update_by_serial = AsyncMock(return_value=device)
        assignment = MagicMock(device_id=99)
        mobile_app_repo.get_assignment_by_id = AsyncMock(return_value=assignment)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo, mobile_app_repo)
        data = DeviceReportIn(
            connection_status="Connected",
            status="Enrolled",
            mobile_app_assignments=[{"assignment_id": 9, "status": "APPLIED"}],
        )
        await svc.report_in("SN-1", data)
        mobile_app_repo.update_assignment_report.assert_not_called()

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
        repo.update_by_serial = AsyncMock(return_value=device)
        mobile_app_repo.get_assignment_by_id = AsyncMock(return_value=None)
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo, mobile_app_repo)
        data = DeviceReportIn(
            connection_status="Connected",
            status="Enrolled",
            mobile_app_assignments=[{"assignment_id": 9, "status": "APPLIED"}],
        )
        await svc.report_in("SN-1", data)
        mobile_app_repo.update_assignment_report.assert_not_called()

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
        repo.update_by_serial = AsyncMock(return_value=device)
        command_repo.get_by_id = AsyncMock(return_value=MagicMock(device_id=1))
        profile_repo.get_assignment_by_id = AsyncMock(return_value=MagicMock(device_id=1))
        mobile_app_repo.get_assignment_by_id = AsyncMock(return_value=MagicMock(device_id=1))
        svc = self.make_service(repo, reconciliation_service, command_repo, profile_repo, mobile_app_repo)
        data = DeviceReportIn(
            connection_status="Connected",
            status="Enrolled",
            commands=[{"command_id": 1, "status": "COMPLETED"}],
            profile_assignments=[{"assignment_id": 7, "status": "APPLIED"}],
            mobile_app_assignments=[{"assignment_id": 9, "status": "APPLIED"}],
        )
        await svc.report_in("SN-1", data)
        command_repo.update_status.assert_awaited_once()
        profile_repo.update_assignment_report.assert_awaited_once_with(7, AssignmentStatus.APPLIED, None)
        mobile_app_repo.update_assignment_report.assert_awaited_once_with(9, AssignmentStatus.APPLIED, None)
        repo.update_by_serial.assert_awaited_once()
