from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.common.enums import ConnectionStatus, EnrollmentStatus


class Wifi(BaseModel):
    ssid: str | None = None
    bssid: str | None = None
    ip_address: str | None = None
    gateway: str | None = None
    dns: list[str] | None = None
    mac_address: str | None = None
    proxy: str | None = None
    signal_strength: int | None = None


class Cellular(BaseModel):
    carrier: str | None = None
    ip_address: str | None = None
    gateway: str | None = None
    dns: list[str] | None = None
    imei: str | None = None
    imsi: str | None = None
    signal_strength: int | None = None
    connection_type: str | None = None
    roaming: bool | None = None


class Network(BaseModel):
    wifi: Wifi | None = None
    cellular: Cellular | None = None


class Certificate(BaseModel):
    common_name: str | None = None
    issuer: str | None = None
    expiry: str | None = None
    type: str | None = None
    fingerprint: str | None = None
    serial_number: str | None = None


class DeviceExtensionAttributeResponse(BaseModel):
    extension_attribute_id: int
    extension_attribute_name: str
    value: str

    model_config = ConfigDict(from_attributes=True)


class DeviceResponse(BaseModel):
    id: int
    name: str
    serial_number: str
    os_version: str
    connection_status: ConnectionStatus
    enrollment_status: EnrollmentStatus
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
    extension_attributes: list[DeviceExtensionAttributeResponse] | None = None

    model_config = ConfigDict(from_attributes=True)


class DeviceExtensionAttributeCreate(BaseModel):
    extension_attribute_id: int
    extension_attribute_name: str
    value: str


class DeviceUpdate(BaseModel):
    connection_status: ConnectionStatus | None = None
    enrollment_status: EnrollmentStatus | None = None
    battery_status: int | None = None
    total_storage: int | None = None
    available_storage: int | None = None
    total_memory: int | None = None
    available_memory: int | None = None
    network: Network | None = None
    certificates: list[Certificate] | None = None
    extension_attributes: list[DeviceExtensionAttributeCreate] | None = None


class DeviceSearchCriteria(BaseModel):
    conjunction: str = "AND"
    criteria: list[dict[str, Any]]
