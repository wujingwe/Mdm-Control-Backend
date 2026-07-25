from __future__ import annotations

from datetime import datetime

from sqlalchemy import Enum, Integer, ForeignKey, DateTime, Text, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.common.enums import CommandType, CommandStatus
from app.devices.models import Device


class Command(Base):
    __tablename__ = "commands"
    __table_args__ = (
        Index("ix_commands_device_id", "device_id"),
        Index("ix_commands_status", "status"),
        Index("ix_commands_command_type", "command_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    command_type: Mapped[CommandType] = mapped_column(Enum(CommandType, native_enum=False, length=30))
    status: Mapped[CommandStatus] = mapped_column(
        Enum(CommandStatus, native_enum=False, length=20),
        default=CommandStatus.PENDING,
    )
    result_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rabbitmq_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    device: Mapped[Device] = relationship(viewonly=True)
