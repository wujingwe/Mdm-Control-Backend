from enum import Enum


class AssignmentStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    REVOKE_PENDING = "REVOKE_PENDING"
    REVOKED = "REVOKED"
    REMOVED = "REMOVED"


class AssignmentDesiredState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class ConnectionStatus(str, Enum):
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    UNKNOWN = "Unknown"


class DeviceStatus(str, Enum):
    ENROLLED = "Enrolled"
    UNENROLLED = "Unenrolled"
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
    LOCK = "LOCK"
    UNLOCK = "UNLOCK"
    WIPE = "WIPE"
    RESTART = "RESTART"
    SHUTDOWN = "SHUTDOWN"


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


class CriteriaType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
