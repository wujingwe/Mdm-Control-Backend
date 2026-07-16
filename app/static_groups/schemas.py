from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StaticGroupCreate(BaseModel):
    name: str
    description: str | None = None
    device_serial_numbers: list[str] = []
    created_by: int = 1


class StaticGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    device_serial_numbers: list[str] | None = None


class StaticGroupResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    created_at: datetime
    created_by: int
    updated_at: datetime | None = None
    device_serial_numbers: list[str] = []

    model_config = ConfigDict(from_attributes=True)
