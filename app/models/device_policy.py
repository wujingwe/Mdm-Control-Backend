from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class DevicePolicy(Base):
    __tablename__ = "device_policies"

    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), primary_key=True)
    policy_id: Mapped[int] = mapped_column(Integer, ForeignKey("policies.id"), primary_key=True)
