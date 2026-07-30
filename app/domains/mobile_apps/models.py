from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Text, Enum, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.core.base import Base, utcnow
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.shared.scope import Scope
from app.domains.profiles.models import ScopeColumnType
from app.domains.users.models import User


class MobileApp(Base):
    __tablename__ = "mobile_apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    package_version: Mapped[str] = mapped_column(String(32))
    package_name: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    scope: Mapped[Scope] = mapped_column(ScopeColumnType)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    creator: Mapped[User] = relationship(User, foreign_keys=[created_by])


class MobileAppAssignment(Base):
    __tablename__ = "mobile_app_assignments"
    __table_args__ = (
        UniqueConstraint("mobile_app_id", "version", "device_id"),
        Index("ix_mobile_app_assignments_mobile_app_id", "mobile_app_id"),
        Index("ix_mobile_app_assignments_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mobile_app_id: Mapped[int] = mapped_column(Integer, ForeignKey("mobile_apps.id", ondelete="CASCADE"))
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, native_enum=False, length=20),
        default=AssignmentStatus.PENDING,
    )
    desired_state: Mapped[AssignmentDesiredState] = mapped_column(
        Enum(AssignmentDesiredState, native_enum=False, length=10),
        default=AssignmentDesiredState.PRESENT,
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
