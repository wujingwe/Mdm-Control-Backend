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


class CommandType(str, Enum):
    """Types of commands that can be sent to a device."""

    CHECK_IN = "CHECK_IN"
    UPDATE_INVENTORY = "UPDATE_INVENTORY"
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"
    WIPE = "WIPE"
    RESTART = "RESTART"
    SHUTDOWN = "SHUTDOWN"
    LOST_MODE = "LOST_MODE"


class CommandStatus(str, Enum):
    """Lifecycle states of a device command.

    Flow: PENDING → SENT → ACKNOWLEDGED → IN_PROGRESS → COMPLETED/FAILED
          CANCELLED can be reached from PENDING or SENT.
    """

    PENDING = "PENDING"  # Created, waiting to be sent to device
    SENT = "SENT"  # Published to RabbitMQ, delivered to device queue
    ACKNOWLEDGED = "ACKNOWLEDGED"  # Device received the command
    IN_PROGRESS = "IN_PROGRESS"  # Device is executing the command
    COMPLETED = "COMPLETED"  # Device finished successfully
    FAILED = "FAILED"  # Device encountered an error
    CANCELLED = "CANCELLED"  # Admin cancelled before device executed
