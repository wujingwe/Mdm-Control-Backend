from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.static_groups.static_group_policy import StaticGroupPolicy  # noqa: F401
from app.static_groups.static_group_device import StaticGroupDevice  # noqa: F401

if TYPE_CHECKING:
    from app.policies.models import Policy


class StaticGroup(Base):
    __tablename__ = "static_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    policies: Mapped[list["Policy"]] = relationship(
        secondary="static_group_policies",
        back_populates="static_groups",
    )
