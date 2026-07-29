from datetime import datetime


from app.infra.common.enums import ConnectionStatus, DeviceStatus
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
    network: Network | dict | None = None
    certificates: list[Certificate] | list | None = None
    extension_attribute_values: list[ExtensionAttributeValueResponse] | None = None


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
