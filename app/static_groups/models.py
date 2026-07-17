from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.devices.models import Device
from app.users.models import User


class StaticGroup(Base):
    __tablename__ = "static_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    creator: Mapped[User] = relationship(User, foreign_keys=[created_by])
    devices: Mapped[list[Device]] = relationship(
        Device,
        secondary="static_group_devices",
        primaryjoin="StaticGroupDevice.static_group_id == StaticGroup.id",
        secondaryjoin="Device.serial_number == StaticGroupDevice.device_serial_number",
    )


class StaticGroupDevice(Base):
    __tablename__ = "static_group_devices"

    static_group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("static_groups.id", ondelete="CASCADE"),
        primary_key=True,
    )
    device_serial_number: Mapped[str] = mapped_column(
        String,
        ForeignKey("devices.serial_number", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
