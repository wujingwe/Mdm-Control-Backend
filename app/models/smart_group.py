from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow
from app.models.smart_group_policy import SmartGroupPolicy  # noqa: F401

if TYPE_CHECKING:
    from app.models.policy import Policy


class SmartGroup(Base):
    __tablename__ = "smart_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    criteria: Mapped[list | None] = mapped_column(JSON, nullable=True)

    policies: Mapped[list["Policy"]] = relationship(
        secondary="smart_group_policies",
        back_populates="smart_groups",
    )
