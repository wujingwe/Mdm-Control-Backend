from app.domains.commands.enums import CommandType, CommandStatus
from app.domains.devices.enums import DeviceStatus, ConnectionStatus
from app.domains.extension_attributes.enums import ExtensionDataType, ExtensionInputType
from app.domains.profiles.enums import AssignmentStatus


class TestEnums:
    def test_extension_data_type_values(self) -> None:
        assert ExtensionDataType.STRING == "string"
        assert ExtensionDataType.INTEGER == "integer"
        assert ExtensionDataType.DATE == "date"

    def test_extension_input_type_values(self) -> None:
        assert ExtensionInputType.TEXT_FIELD == "Text field"
        assert ExtensionInputType.POPUP_MENU == "Pop-up menu"

    def test_command_type_values(self) -> None:
        assert CommandType.LOCK == "LOCK"
        assert CommandType.WIPE == "WIPE"
        assert CommandType.RESTART == "RESTART"
        assert CommandType.SHUTDOWN == "SHUTDOWN"
        assert CommandType.CHECK_IN == "CHECK_IN"
        assert CommandType.UNLOCK == "UNLOCK"

    def test_command_status_values(self) -> None:
        assert CommandStatus.PENDING == "PENDING"
        assert CommandStatus.SENT == "SENT"
        assert CommandStatus.ACKNOWLEDGED == "ACKNOWLEDGED"
        assert CommandStatus.IN_PROGRESS == "IN_PROGRESS"
        assert CommandStatus.COMPLETED == "COMPLETED"
        assert CommandStatus.FAILED == "FAILED"
        assert CommandStatus.CANCELLED == "CANCELLED"

    def test_assignment_status_values(self) -> None:
        assert AssignmentStatus.PENDING == "PENDING"
        assert AssignmentStatus.APPLIED == "APPLIED"

    def test_connection_status_values(self) -> None:
        assert ConnectionStatus.CONNECTED == "Connected"
        assert ConnectionStatus.DISCONNECTED == "Disconnected"
        assert ConnectionStatus.UNKNOWN == "Unknown"

    def test_device_status_values(self) -> None:
        assert DeviceStatus.ENROLLED == "Enrolled"
        assert DeviceStatus.UNENROLLED == "Unenrolled"
        assert DeviceStatus.PENDING == "Pending"
        assert DeviceStatus.UNKNOWN == "Unknown"
