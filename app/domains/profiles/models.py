from datetime import datetime
from typing import Any

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
    JSON,
    TypeDecorator,
    Dialect,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.core.base import Base, utcnow
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.shared.scope import Scope
from app.domains.users.models import User


class ScopeColumnType(TypeDecorator[Scope]):
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Scope | dict[str, Any] | None, dialect: Dialect) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return value.model_dump()

    def process_result_value(self, value: dict[str, Any] | None, dialect: Dialect) -> Scope | None:
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
    policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    scope: Mapped[Scope] = mapped_column(ScopeColumnType, default=Scope)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    creator: Mapped[User] = relationship(User, foreign_keys=[created_by])


class ProfileAssignment(Base):
    __tablename__ = "profile_assignments"
    __table_args__ = (
        UniqueConstraint("profile_id", "profile_version", "device_id"),
        Index("ix_profile_assignments_profile_id", "profile_id"),
        Index("ix_profile_assignments_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"))
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, native_enum=False, length=20),
        default=AssignmentStatus.PENDING,
    )
    desired_state: Mapped[AssignmentDesiredState] = mapped_column(
        Enum(AssignmentDesiredState, native_enum=False, length=10),
        default=AssignmentDesiredState.PRESENT,
    )
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
