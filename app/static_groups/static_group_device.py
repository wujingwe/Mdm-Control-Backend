from sqlalchemy import Integer, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base


class StaticGroupDevice(Base):
    __tablename__ = "static_group_devices"

    static_group_id: Mapped[int] = mapped_column(Integer, ForeignKey("static_groups.id"), primary_key=True)
    device_serial_number: Mapped[str] = mapped_column(String(30), ForeignKey("devices.serial_number"), primary_key=True)
