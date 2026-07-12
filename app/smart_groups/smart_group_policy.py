from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base


class SmartGroupPolicy(Base):
    __tablename__ = "smart_group_policies"

    smart_group_id: Mapped[int] = mapped_column(Integer, ForeignKey("smart_groups.id", ondelete="CASCADE"), primary_key=True)
    policy_id: Mapped[int] = mapped_column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), primary_key=True)
