from datetime import datetime

from pydantic import BaseModel


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
    device_serial_numbers: list[str] = []
    created_at: datetime
    created_by: int
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
