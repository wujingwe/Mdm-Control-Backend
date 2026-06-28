from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow
from app.models.device_policy import DevicePolicy  # noqa: F401
from app.models.types import CertificateListType, NetworkInfoType
from app.schemas.device import CertificateInfo, NetworkInfo

if TYPE_CHECKING:
    from app.models.policy import Policy


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    serial_number: Mapped[str] = mapped_column(String(30), unique=True)
    os_version: Mapped[str] = mapped_column(String(20))
    connection_status: Mapped[str] = mapped_column(String(20))
    enrollment_status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    battery_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_storage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_storage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_memory: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_memory: Mapped[int | None] = mapped_column(Integer, nullable=True)
    network: Mapped[NetworkInfo | None] = mapped_column(NetworkInfoType, nullable=True)
    certificates: Mapped[list[CertificateInfo] | None] = mapped_column(CertificateListType, nullable=True)

    policies: Mapped[list["Policy"]] = relationship(
        secondary="device_policies",
        back_populates="devices",
    )
