from datetime import datetime


from app.common.enums import CommandType, CommandStatus
from app.common.schemas import CamelModel


class CommandCreate(CamelModel):
    command_type: CommandType


class CommandResponse(CamelModel):
    id: int
    device_id: int
    command_type: CommandType
    status: CommandStatus
    result_message: str | None = None
    created_by: int
    created_at: datetime
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    completed_at: datetime | None = None
