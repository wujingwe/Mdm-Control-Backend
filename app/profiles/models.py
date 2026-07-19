from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, DateTime, JSON, TypeDecorator, Dialect, \
    UniqueConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.common.enums import AssignmentStatus
from app.common.schemas import Scope
from app.users.models import User


class ScopeColumnType(TypeDecorator[Scope]):
    impl = JSON
    cache_ok = True

    def process_bind_param(
        self, value: Scope | dict[str, Any] | None, dialect: Dialect
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return value.model_dump()

    def process_result_value(
        self, value: dict[str, Any] | None, dialect: Dialect
    ) -> Scope | None:
        if value is None:
            return None
        return Scope.model_validate(value)


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (Index("ix_profiles_created_by", "created_by"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    scope: Mapped[Scope] = mapped_column(ScopeColumnType, default=Scope)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    creator: Mapped[User | None] = relationship(User, foreign_keys=[created_by])


class ProfileAssignment(Base):
    __tablename__ = "profile_assignments"
    __table_args__ = (
        UniqueConstraint("profile_id", "profile_version", "device_id"),
        Index("ix_profile_assignments_profile_id", "profile_id"),
        Index("ix_profile_assignments_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profiles.id", ondelete="CASCADE")
    )
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(
        Enum(AssignmentStatus, native_enum=False, length=20),
        default=AssignmentStatus.PENDING,
    )
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)