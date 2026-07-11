from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.device_policy import DevicePolicy  # noqa: F401
from app.models.smart_group_policy import SmartGroupPolicy  # noqa: F401
from app.models.static_group_policy import StaticGroupPolicy  # noqa: F401

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.smart_group import SmartGroup
    from app.models.static_group import StaticGroup


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)
    scope: Mapped[str] = mapped_column(String(100))
    rollout_state: Mapped[str] = mapped_column(String(20))
    target_devices: Mapped[int] = mapped_column(Integer, default=0)
    applied_devices: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    devices: Mapped[list["Device"]] = relationship(
        secondary="device_policies",
        back_populates="policies",
    )

    smart_groups: Mapped[list["SmartGroup"]] = relationship(
        secondary="smart_group_policies",
        back_populates="policies",
    )

    static_groups: Mapped[list["StaticGroup"]] = relationship(
        secondary="static_group_policies",
        back_populates="policies",
    )
