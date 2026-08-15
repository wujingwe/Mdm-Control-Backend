from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Enum,
    String,
    Integer,
    DateTime,
    Index,
    UniqueConstraint,
    Text,
    ForeignKey,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.core.base import Base, utcnow
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.profiles.models import Profile, ProfileAssignment
from app.infra.core.types import CertificateListType, NetworkInfoType
from app.domains.devices.schemas import Certificate, Network

_latest_profile_assignments = (
    select(ProfileAssignment.profile_id, ProfileAssignment.device_id)
    .group_by(ProfileAssignment.profile_id, ProfileAssignment.device_id)
    .subquery()
)

_latest_mobile_app_assignments = (
    select(MobileAppAssignment.mobile_app_id, MobileAppAssignment.device_id)
    .group_by(MobileAppAssignment.mobile_app_id, MobileAppAssignment.device_id)
    .subquery()
)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_connection_status", "connection_status"),
        Index("ix_devices_status", "status"),
        Index("ix_devices_os_version", "os_version"),
        CheckConstraint(
            "connection_status IN ('CONNECTED', 'DISCONNECTED', 'UNKNOWN')",
            name="ck_devices_connection_status",
        ),
        CheckConstraint(
            "status IN ('ENROLLED', 'UNENROLLED', 'PENDING', 'UNKNOWN')",
            name="ck_devices_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    serial_number: Mapped[str] = mapped_column(String(30), unique=True)
    os_version: Mapped[str] = mapped_column(String(20))
    connection_status: Mapped[ConnectionStatus] = mapped_column(Enum(ConnectionStatus, native_enum=False, length=20))
    status: Mapped[DeviceStatus] = mapped_column(Enum(DeviceStatus, native_enum=False, length=20))
    last_enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    battery_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_storage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_storage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_memory: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_memory: Mapped[int | None] = mapped_column(Integer, nullable=True)
    network: Mapped[Network | None] = mapped_column(NetworkInfoType, nullable=True)
    certificates: Mapped[list[Certificate] | None] = mapped_column(CertificateListType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    extension_attribute_values: Mapped[list["DeviceExtensionAttributeValue"]] = relationship(
        primaryjoin="Device.id == DeviceExtensionAttributeValue.device_id",
        lazy="noload",
    )

    profiles: Mapped[list["Profile"]] = relationship(
        "Profile",
        secondary=_latest_profile_assignments,
        primaryjoin=lambda: Device.id == _latest_profile_assignments.c.device_id,
        secondaryjoin=lambda: Profile.id == _latest_profile_assignments.c.profile_id,
        viewonly=True,
        lazy="noload",
    )

    mobile_apps: Mapped[list["MobileApp"]] = relationship(
        "MobileApp",
        secondary=_latest_mobile_app_assignments,
        primaryjoin=lambda: Device.id == _latest_mobile_app_assignments.c.device_id,
        secondaryjoin=lambda: MobileApp.id == _latest_mobile_app_assignments.c.mobile_app_id,
        viewonly=True,
        lazy="noload",
    )


class DeviceExtensionAttributeValue(Base):
    __tablename__ = "device_extension_attribute_values"
    __table_args__ = (
        UniqueConstraint("device_id", "extension_attribute_id"),
        Index("ix_device_ext_attr_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    extension_attribute_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("extension_attributes.id", ondelete="CASCADE")
    )
    extension_attribute_name: Mapped[str] = mapped_column(String(100))
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
