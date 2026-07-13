from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.static_groups.static_group_device import StaticGroupDevice  # noqa: F401
from app.users.models import User


class StaticGroup(Base):
    __tablename__ = "static_groups"
    __table_args__ = (Index("ix_static_groups_created_by", "created_by"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    creator: Mapped[User | None] = relationship(User, foreign_keys=[created_by])
