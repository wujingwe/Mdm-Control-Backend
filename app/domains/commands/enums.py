from enum import Enum


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

    PENDING = "PENDING"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
