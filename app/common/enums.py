import sqlalchemy as sa


# Profile scope target types
TargetType = sa.Enum("ALL_DEVICES", "SMART_GROUP", "STATIC_GROUP", "DEVICE", name="target_type", native_enum=False, length=20)

# Profile assignment source
AssignmentSource = sa.Enum("DIRECT", "SMART_GROUP", "STATIC_GROUP", "ALL_DEVICES", name="assignment_source", native_enum=False, length=20)

# Profile assignment status
AssignmentStatus = sa.Enum("PENDING", "APPLIED", "FAILED", "REVOKED", "REMOVED", name="assignment_status", native_enum=False, length=20)

# Device connection status
ConnectionStatus = sa.Enum("Online", "Offline", "Pending", name="connection_status", native_enum=False, length=20)

# Device enrollment status
EnrollmentStatus = sa.Enum("Compliant", "Non-compliant", "Needs attention", "Enrolled", "Pending", "Unknown", name="enrollment_status", native_enum=False, length=20)

# Extension attribute data type
ExtensionDataType = sa.Enum("string", "integer", "date", name="extension_data_type", native_enum=False, length=20)

# Extension attribute input type
ExtensionInputType = sa.Enum("Text field", "Pop-up menu", name="extension_input_type", native_enum=False, length=20)
