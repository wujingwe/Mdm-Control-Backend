from enum import Enum


class AssignmentStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    REVOKE_PENDING = "REVOKE_PENDING"
    REVOKED = "REVOKED"


class AssignmentDesiredState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
