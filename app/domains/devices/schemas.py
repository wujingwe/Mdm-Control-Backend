from datetime import datetime


from app.domains.commands.enums import CommandStatus
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.mobile_apps.schemas import MobileAppAssignmentReportIn, MobileAppResponse
from app.domains.profiles.enums import AssignmentStatus
from app.domains.profiles.schemas.profile import ProfileResponse
from app.infra.common.schemas import CamelModel


class Wifi(CamelModel):
    ssid: str | None = None
    bssid: str | None = None
    ip_address: str | None = None
    gateway: str | None = None
    dns: list[str] | None = None
    mac_address: str | None = None
    proxy: str | None = None
    signal_strength: int | None = None


class Cellular(CamelModel):
    carrier: str | None = None
    ip_address: str | None = None
    gateway: str | None = None
    dns: list[str] | None = None
    imei: str | None = None
    imsi: str | None = None
    signal_strength: int | None = None
    connection_type: str | None = None
    roaming: bool | None = None


class Network(CamelModel):
    wifi: Wifi | None = None
    cellular: Cellular | None = None


class Certificate(CamelModel):
    common_name: str | None = None
    issuer: str | None = None
    expiry: str | None = None
    type: str | None = None
    fingerprint: str | None = None
    serial_number: str | None = None


class ExtensionAttributeValueResponse(CamelModel):
    extension_attribute_id: int
    extension_attribute_name: str
    value: str


class DeviceResponse(CamelModel):
    id: int
    name: str
    serial_number: str
    os_version: str
    connection_status: ConnectionStatus
    status: DeviceStatus
    created_at: datetime
    updated_at: datetime
    last_enrolled_at: datetime
    battery_status: int | None = None
    total_storage: int | None = None
    available_storage: int | None = None
    total_memory: int | None = None
    available_memory: int | None = None
    network: Network | None = None
    certificates: list[Certificate] | None = None
    extension_attribute_values: list[ExtensionAttributeValueResponse] | None = None
    profiles: list[ProfileResponse] | None = None
    mobile_apps: list[MobileAppResponse] | None = None


class ExtensionAttributeValueCreate(CamelModel):
    extension_attribute_id: int
    extension_attribute_name: str
    value: str


class DeviceUpdate(CamelModel):
    connection_status: ConnectionStatus | None = None
    status: DeviceStatus | None = None
    battery_status: int | None = None
    total_storage: int | None = None
    available_storage: int | None = None
    total_memory: int | None = None
    available_memory: int | None = None
    network: Network | None = None
    certificates: list[Certificate] | None = None
    extension_attribute_values: list[ExtensionAttributeValueCreate] | None = None


class DeviceAuthResponse(CamelModel):
    serial_number: str
    enrolled: bool
    cert_valid_until: datetime


class DeviceRegisterRequest(CamelModel):
    name: str
    os_version: str
    certificates: list[Certificate] | None = None


class CommandReportIn(CamelModel):
    command_id: int
    status: CommandStatus
    result_message: str | None = None


class ProfileAssignmentReportIn(CamelModel):
    assignment_id: int
    status: AssignmentStatus
    result_message: str | None = None


class DeviceReportIn(CamelModel):
    connection_status: ConnectionStatus
    status: DeviceStatus
    battery_status: int | None = None
    total_storage: int | None = None
    available_storage: int | None = None
    total_memory: int | None = None
    available_memory: int | None = None
    network: Network | None = None
    commands: list[CommandReportIn] | None = None
    profile_assignments: list[ProfileAssignmentReportIn] | None = None
    mobile_app_assignments: list[MobileAppAssignmentReportIn] | None = None
