from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utcnow
from app.models.group_policy import GroupPolicy  # noqa: F401

if TYPE_CHECKING:
    from app.models.policy import Policy


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    criteria: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_smart: Mapped[bool] = mapped_column(Boolean, default=False)
    display_columns: Mapped[list | None] = mapped_column(JSON, nullable=True)
    device_serial_numbers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    policies: Mapped[list["Policy"]] = relationship(
        secondary="group_policies",
        back_populates="groups",
    )
