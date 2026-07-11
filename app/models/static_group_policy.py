from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class StaticGroupPolicy(Base):
    __tablename__ = "static_group_policies"

    static_group_id: Mapped[int] = mapped_column(Integer, ForeignKey("static_groups.id"), primary_key=True)
    policy_id: Mapped[int] = mapped_column(Integer, ForeignKey("policies.id"), primary_key=True)
