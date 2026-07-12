from datetime import datetime

from sqlalchemy import Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base, utcnow


class ProfileAssignment(Base):
    __tablename__ = "profile_assignments"
    __table_args__ = (UniqueConstraint("profile_id", "device_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"))
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"))
    source: Mapped[str] = mapped_column(String(20))
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
