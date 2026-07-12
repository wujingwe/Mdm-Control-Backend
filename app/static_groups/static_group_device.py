from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base


class StaticGroupDevice(Base):
    __tablename__ = "static_group_devices"

    static_group_id: Mapped[int] = mapped_column(Integer, ForeignKey("static_groups.id", ondelete="CASCADE"), primary_key=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
