from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base, utcnow
from app.types import CertificateListType, NetworkInfoType
from app.devices.schemas import Certificate, Network


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_connection_status", "connection_status"),
        Index("ix_devices_enrollment_status", "enrollment_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    serial_number: Mapped[str] = mapped_column(String(30), unique=True)
    os_version: Mapped[str] = mapped_column(String(20))
    connection_status: Mapped[str] = mapped_column(String(20))
    enrollment_status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    last_enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    battery_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_storage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_storage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_memory: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_memory: Mapped[int | None] = mapped_column(Integer, nullable=True)
    network: Mapped[Network | None] = mapped_column(NetworkInfoType, nullable=True)
    certificates: Mapped[list[Certificate] | None] = mapped_column(CertificateListType, nullable=True)
