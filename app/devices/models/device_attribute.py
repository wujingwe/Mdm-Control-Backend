from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base, utcnow


class DeviceExtensionAttribute(Base):
    __tablename__ = "device_extension_attribute_values"
    __table_args__ = (
        UniqueConstraint("device_id", "extension_attribute_id"),
        Index("ix_device_ext_attr_device_id", "device_id"),
        Index("ix_device_ext_attr_attr_id", "extension_attribute_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    extension_attribute_id: Mapped[int] = mapped_column(Integer, ForeignKey("extension_attributes.id", ondelete="CASCADE"))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
