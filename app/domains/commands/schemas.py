from app.infra.common.enums import CommandType
from app.infra.common.schemas import CamelModel
from datetime import datetime


class CommandCreate(CamelModel):
    command_type: CommandType


class CommandResponse(CamelModel):
    id: int
    device_id: int
    command_type: CommandType
    status: str
    created_by: int
    created_at: datetime
    sent_at: datetime | None = None
    acknowledged_at: datetime | None = None
    completed_at: datetime | None = None
    result_message: str | None = None
    rabbitmq_message_id: str | None = None
