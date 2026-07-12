from datetime import datetime

from sqlalchemy import Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base, utcnow


class StaticGroupDevice(Base):
    __tablename__ = "static_group_devices"

    static_group_id: Mapped[int] = mapped_column(Integer, ForeignKey("static_groups.id", ondelete="CASCADE"), primary_key=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
