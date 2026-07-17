from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enums import CommandType, CommandStatus


class CommandCreate(BaseModel):
    command_type: CommandType
    parameters: dict | None = None


class CommandResponse(BaseModel):
    id: int
    device_id: int
    command_type: CommandType
    parameters: dict | None = None
    status: CommandStatus
    result_message: str | None = None
    created_by: int | None = None
    created_at: datetime
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
