from enum import Enum


class ConnectionStatus(str, Enum):
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"
    UNKNOWN = "Unknown"


class DeviceStatus(str, Enum):
    ENROLLED = "Enrolled"
    UNENROLLED = "Unenrolled"
    PENDING = "Pending"
    UNKNOWN = "Unknown"
