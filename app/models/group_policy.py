from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class GroupPolicy(Base):
    __tablename__ = "group_policies"

    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), primary_key=True)
    policy_id: Mapped[int] = mapped_column(Integer, ForeignKey("policies.id"), primary_key=True)
