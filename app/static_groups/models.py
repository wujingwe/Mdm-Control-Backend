from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.static_groups.static_group_device import StaticGroupDevice  # noqa: F401

if TYPE_CHECKING:
    from app.users.models import User


class StaticGroup(Base):
    __tablename__ = "static_groups"
    __table_args__ = (Index("ix_static_groups_created_by", "created_by"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
