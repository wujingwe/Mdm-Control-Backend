class TestEnums:
    def test_target_type_values(self):
        from app.common.enums import TargetType

        assert TargetType.ALL_DEVICES == "ALL_DEVICES"
        assert TargetType.DEVICE == "DEVICE"
        assert TargetType.STATIC_GROUP == "STATIC_GROUP"
        assert TargetType.SMART_GROUP == "SMART_GROUP"

    def test_extension_data_type_values(self):
        from app.common.enums import ExtensionDataType

        assert ExtensionDataType.STRING == "string"
        assert ExtensionDataType.INTEGER == "integer"
        assert ExtensionDataType.DATE == "date"

    def test_extension_input_type_values(self):
        from app.common.enums import ExtensionInputType

        assert ExtensionInputType.TEXT_FIELD == "Text field"
        assert ExtensionInputType.POPUP_MENU == "Pop-up menu"

    def test_command_type_values(self):
        from app.common.enums import CommandType

        assert CommandType.LOCK == "LOCK"
        assert CommandType.WIPE == "WIPE"
        assert CommandType.RESTART == "RESTART"
        assert CommandType.SHUTDOWN == "SHUTDOWN"
        assert CommandType.CHECK_IN == "CHECK_IN"
        assert CommandType.UNLOCK == "UNLOCK"

    def test_command_status_values(self):
        from app.common.enums import CommandStatus

        assert CommandStatus.PENDING == "PENDING"
        assert CommandStatus.SENT == "SENT"
        assert CommandStatus.ACKNOWLEDGED == "ACKNOWLEDGED"
        assert CommandStatus.IN_PROGRESS == "IN_PROGRESS"
        assert CommandStatus.COMPLETED == "COMPLETED"
        assert CommandStatus.FAILED == "FAILED"
        assert CommandStatus.CANCELLED == "CANCELLED"

    def test_assignment_source_values(self):
        from app.common.enums import AssignmentSource

        assert AssignmentSource.DIRECT == "DIRECT"
        assert AssignmentSource.SMART_GROUP == "SMART_GROUP"
        assert AssignmentSource.STATIC_GROUP == "STATIC_GROUP"

    def test_connection_status_values(self):
        from app.common.enums import ConnectionStatus

        assert ConnectionStatus.ONLINE == "Online"
        assert ConnectionStatus.OFFLINE == "Offline"
        assert ConnectionStatus.PENDING == "Pending"

    def test_enrollment_status_values(self):
        from app.common.enums import EnrollmentStatus

        assert EnrollmentStatus.COMPLIANT == "Compliant"
        assert EnrollmentStatus.ENROLLED == "Enrolled"
        assert EnrollmentStatus.PENDING == "Pending"
