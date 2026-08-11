from datetime import datetime, timezone

from app.domains.commands.enums import CommandStatus
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.devices.schemas import (
    Certificate,
    Cellular,
    DeviceReportIn,
    DeviceResponse,
    DeviceUpdate,
    Network,
    Wifi, ExtensionAttributeValueCreate, CommandReportIn, ProfileAssignmentReportIn,
)
from app.domains.mobile_apps.schemas import MobileAppAssignmentReportIn
from app.domains.profiles.enums import AssignmentStatus

_DEVICE_FIELDS = {
    "id": 1,
    "serial_number": "SN001",
    "name": "Test",
    "os_version": "14.0",
    "connection_status": "Connected",
    "status": "Enrolled",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "last_enrolled_at": datetime.now(timezone.utc),
}


class TestDeviceResponseSchema:
    def test_response_from_attributes(self) -> None:
        data = DeviceResponse(**_DEVICE_FIELDS)
        assert data.id == 1
        assert data.name == "Test"

    def test_optional_fields_default_to_none(self) -> None:
        data = DeviceResponse(**_DEVICE_FIELDS)
        assert data.battery_status is None
        assert data.network is None
        assert data.certificates is None

    def test_network_and_certificates_default_to_none(self) -> None:
        data = DeviceResponse(**_DEVICE_FIELDS)
        assert data.network is None
        assert data.certificates is None

    def test_with_network_info(self) -> None:
        wifi = Wifi(ssid="Office", bssid="00:11:22:33:44:55", signal_strength=-45)
        net = Network(wifi=wifi)
        data = DeviceResponse(**_DEVICE_FIELDS, network=net)
        assert data.network.wifi.ssid == "Office"
        assert data.network.wifi.bssid == "00:11:22:33:44:55"
        assert data.network.wifi.signal_strength == -45
        assert data.network.cellular is None

    def test_with_network_cellular(self) -> None:
        cell = Cellular(carrier="AT&T", imei="123456789012345", roaming=False)
        net = Network(cellular=cell)
        data = DeviceResponse(**_DEVICE_FIELDS, network=net)
        assert data.network.cellular.carrier == "AT&T"
        assert data.network.cellular.imei == "123456789012345"
        assert data.network.cellular.roaming is False
        assert data.network.wifi is None

    def test_with_certificates(self) -> None:
        certs = [
            Certificate(common_name="example.com", issuer="CA Inc", type="identity"),
            Certificate(common_name="backup.example.com", fingerprint="AB:CD:EF"),
        ]
        data = DeviceResponse(**_DEVICE_FIELDS, certificates=certs)
        certificates = data.certificates
        assert len(certificates) == 2
        assert certificates[0].common_name == "example.com"
        assert certificates[0].type == "identity"
        assert certificates[1].fingerprint == "AB:CD:EF"


class TestWifiSchema:
    def test_all_fields_default_to_none(self) -> None:
        w = Wifi()
        assert w.ssid is None
        assert w.bssid is None
        assert w.ip_address is None
        assert w.gateway is None
        assert w.dns is None
        assert w.mac_address is None
        assert w.proxy is None
        assert w.signal_strength is None

    def test_constructor(self) -> None:
        w = Wifi(ssid="Home", mac_address="aa:bb:cc:dd:ee:ff", signal_strength=-60)
        assert w.ssid == "Home"
        assert w.mac_address == "aa:bb:cc:dd:ee:ff"
        assert w.signal_strength == -60


class TestCellularSchema:
    def test_all_fields_default_to_none(self) -> None:
        c = Cellular()
        assert c.carrier is None
        assert c.ip_address is None
        assert c.imei is None
        assert c.roaming is None

    def test_constructor(self) -> None:
        c = Cellular(carrier="Verizon", connection_type="5G", roaming=True)
        assert c.carrier == "Verizon"
        assert c.connection_type == "5G"
        assert c.roaming is True


class TestNetworkSchema:
    def test_both_subfields_default_to_none(self) -> None:
        n = Network()
        assert n.wifi is None
        assert n.cellular is None

    def test_with_wifi(self) -> None:
        n = Network(wifi=Wifi(ssid="Guest"))
        assert n.wifi.ssid == "Guest"
        assert n.cellular is None

    def test_with_cellular(self) -> None:
        n = Network(cellular=Cellular(imei="000000000000000"))
        assert n.cellular.imei == "000000000000000"
        assert n.wifi is None

    def test_model_dump_roundtrip(self) -> None:
        n = Network(wifi=Wifi(ssid="Test"), cellular=Cellular(carrier="T-Mobile"))
        dumped = n.model_dump()
        loaded = Network.model_validate(dumped)
        assert loaded.wifi.ssid == "Test"
        assert loaded.cellular.carrier == "T-Mobile"


class TestCertificateSchema:
    def test_all_fields_default_to_none(self) -> None:
        c = Certificate()
        assert c.common_name is None
        assert c.issuer is None
        assert c.expiry is None
        assert c.type is None
        assert c.fingerprint is None
        assert c.serial_number is None

    def test_constructor(self) -> None:
        c = Certificate(common_name="example.com", issuer="CA Inc", type="identity")
        assert c.common_name == "example.com"
        assert c.issuer == "CA Inc"
        assert c.type == "identity"

    def test_model_dump_roundtrip(self) -> None:
        c = Certificate(common_name="test.com", fingerprint="12:34:56")
        dumped = c.model_dump()
        loaded = Certificate.model_validate(dumped)
        assert loaded.common_name == "test.com"
        assert loaded.fingerprint == "12:34:56"


class TestDeviceUpdateSchema:
    def test_update_all_fields(self) -> None:
        data = DeviceUpdate(
            connection_status=ConnectionStatus.DISCONNECTED,
            status=DeviceStatus.UNENROLLED,
            battery_status=50,
            total_storage=256,
            available_storage=128,
            total_memory=16,
            available_memory=8,
            network=Network(wifi=Wifi(ssid="Home")),
            certificates=[Certificate(common_name="test.com")],
            extension_attribute_values=[
                ExtensionAttributeValueCreate(
                    extension_attribute_id=1,
                    extension_attribute_name="custom_field",
                    value="test_value",
                ),
            ],
        )
        assert data.connection_status == "Disconnected"
        assert data.status == "Unenrolled"
        assert data.battery_status == 50
        assert data.network.wifi.ssid == "Home"
        assert len(data.certificates) == 1
        assert len(data.extension_attribute_values) == 1

    def test_update_partial(self) -> None:
        data = DeviceUpdate(connection_status=ConnectionStatus.CONNECTED)
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {"connection_status": "Connected"}

    def test_update_empty(self) -> None:
        data = DeviceUpdate()
        assert data.model_dump(exclude_unset=True) == {}

    def test_update_ext_attrs_optional(self) -> None:
        data = DeviceUpdate()
        assert data.extension_attribute_values is None

    def test_update_ext_attrs_empty_list(self) -> None:
        data = DeviceUpdate(extension_attribute_values=[])
        assert data.extension_attribute_values == []


class TestDeviceReportInSchema:
    def test_required_fields(self) -> None:
        data = DeviceReportIn(connection_status=ConnectionStatus.CONNECTED, status=DeviceStatus.ENROLLED)
        assert data.connection_status == "Connected"
        assert data.status == "Enrolled"
        assert data.commands is None
        assert data.profile_assignments is None
        assert data.mobile_app_assignments is None

    def test_commands_population(self) -> None:
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            commands=[
                CommandReportIn(
                    command_id=1,
                    status=CommandStatus.COMPLETED,
                    result_message="done",
                ),
            ],
        )
        commands = data.commands
        assert len(commands) == 1
        assert commands[0].command_id == 1
        assert commands[0].status == "COMPLETED"

    def test_profile_assignments_population(self) -> None:
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            profile_assignments=[
                ProfileAssignmentReportIn(
                    assignment_id=7,
                    status=AssignmentStatus.APPLIED,
                    result_message="applied",
                ),
            ],
        )
        profile_assignments = data.profile_assignments
        assert len(profile_assignments) == 1
        assert profile_assignments[0].assignment_id == 7
        assert profile_assignments[0].status == "APPLIED"
        assert profile_assignments[0].result_message == "applied"

    def test_profile_assignments_omit_result_message(self) -> None:
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            profile_assignments=[
                ProfileAssignmentReportIn(
                    assignment_id=7,
                    status=AssignmentStatus.SENT,
                ),
            ],
        )
        profile_assignments = data.profile_assignments
        assert len(profile_assignments) == 1
        assert profile_assignments[0].result_message is None

    def test_mobile_app_assignments_population(self) -> None:
        data = DeviceReportIn(
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
            mobile_app_assignments=[
                MobileAppAssignmentReportIn(
                    assignment_id=9,
                    status=AssignmentStatus.FAILED,
                    result_message="install error"
                ),
            ],
        )
        mobile_app_assignments = data.mobile_app_assignments
        assert len(mobile_app_assignments) == 1
        assert mobile_app_assignments[0].assignment_id == 9
        assert mobile_app_assignments[0].status == "FAILED"
        assert mobile_app_assignments[0].result_message == "install error"

    def test_all_report_items_together(self) -> None:
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
        assert data.commands is not None and len(data.commands) == 1
        assert data.profile_assignments is not None and len(data.profile_assignments) == 1
        assert data.mobile_app_assignments is not None and len(data.mobile_app_assignments) == 1

    def test_dump_excludes_report_lists_when_absent(self) -> None:
        data = DeviceReportIn(connection_status=ConnectionStatus.CONNECTED, status=DeviceStatus.ENROLLED)
        dumped = data.model_dump(exclude_unset=True)
        assert "commands" not in dumped
        assert "profile_assignments" not in dumped
        assert "mobile_app_assignments" not in dumped

    def test_camel_case_alias_population(self) -> None:
        data = DeviceReportIn.model_validate(
            {
                "connectionStatus": "Connected",
                "status": "Enrolled",
                "profileAssignments": [{"assignmentId": 7, "status": "APPLIED"}],
                "mobileAppAssignments": [{"assignmentId": 9, "status": "APPLIED"}],
            }
        )
        profile_assignments = data.profile_assignments
        assert len(profile_assignments) == 1
        assert profile_assignments[0].assignment_id == 7

        mobile_app_assignments = data.mobile_app_assignments
        assert len(mobile_app_assignments) == 1
        assert mobile_app_assignments[0].assignment_id == 9
