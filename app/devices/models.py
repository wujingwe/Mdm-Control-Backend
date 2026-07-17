from datetime import datetime

from sqlalchemy import (
    Enum,
    String,
    Integer,
    DateTime,
    Index,
    UniqueConstraint,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.common.enums import ConnectionStatus, EnrollmentStatus
from app.types import CertificateListType, NetworkInfoType
from app.profiles.models import Profile
from app.profiles.models import ProfileAssignment  # noqa: F401 — used in relationship string


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_connection_status", "connection_status"),
        Index("ix_devices_enrollment_status", "enrollment_status"),
        Index("ix_devices_os_version", "os_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    serial_number: Mapped[str] = mapped_column(String(30), unique=True)
    os_version: Mapped[str] = mapped_column(String(20))
    connection_status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus, native_enum=False, length=20)
    )
    enrollment_status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, native_enum=False, length=20)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
    last_enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    battery_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_storage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_storage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_memory: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_memory: Mapped[int | None] = mapped_column(Integer, nullable=True)
    network: Mapped[dict | None] = mapped_column(NetworkInfoType, nullable=True)
    certificates: Mapped[list | None] = mapped_column(
        CertificateListType, nullable=True
    )

    extension_attributes: Mapped[list["DeviceExtensionAttribute"]] = relationship(
        primaryjoin="Device.id == DeviceExtensionAttribute.device_id",
        viewonly=True,
        lazy="noload",
    )

    profiles: Mapped[list["Profile"]] = relationship(
        secondary="profile_assignments",
        primaryjoin="Device.id == ProfileAssignment.device_id",
        secondaryjoin="Profile.id == ProfileAssignment.profile_id",
        viewonly=True,
    )


class DeviceExtensionAttribute(Base):
    __tablename__ = "device_extension_attribute_values"
    __table_args__ = (
        UniqueConstraint("device_id", "extension_attribute_id"),
        Index("ix_device_ext_attr_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE")
    )
    extension_attribute_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("extension_attributes.id", ondelete="CASCADE")
    )
    extension_attribute_name: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
