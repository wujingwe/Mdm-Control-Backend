from enum import Enum


class TargetType(str, Enum):
    ALL_DEVICES = "ALL_DEVICES"
    SMART_GROUP = "SMART_GROUP"
    STATIC_GROUP = "STATIC_GROUP"
    DEVICE = "DEVICE"


class AssignmentSource(str, Enum):
    DIRECT = "DIRECT"
    SMART_GROUP = "SMART_GROUP"
    STATIC_GROUP = "STATIC_GROUP"
    ALL_DEVICES = "ALL_DEVICES"


class AssignmentStatus(str, Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    REVOKED = "REVOKED"
    REMOVED = "REMOVED"


class ConnectionStatus(str, Enum):
    ONLINE = "Online"
    OFFLINE = "Offline"
    PENDING = "Pending"


class EnrollmentStatus(str, Enum):
    COMPLIANT = "Compliant"
    NON_COMPLIANT = "Non-compliant"
    NEEDS_ATTENTION = "Needs attention"
    ENROLLED = "Enrolled"
    PENDING = "Pending"
    UNKNOWN = "Unknown"


class ExtensionDataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DATE = "date"


class ExtensionInputType(str, Enum):
    TEXT_FIELD = "Text field"
    POPUP_MENU = "Pop-up menu"
