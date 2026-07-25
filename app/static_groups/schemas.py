from datetime import datetime

from app.common.schemas import CamelModel
from app.devices.schemas import DeviceResponse


class StaticGroupCreate(CamelModel):
    name: str
    description: str | None = None
    device_serial_numbers: list[str] = []


class StaticGroupUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    device_serial_numbers: list[str] | None = None


class StaticGroupResponse(CamelModel):
    id: int
    name: str
    description: str | None = None
    created_by: int
    created_at: datetime
    updated_at: datetime | None = None
    devices: list[DeviceResponse]
