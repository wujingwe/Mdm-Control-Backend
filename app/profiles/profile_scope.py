from sqlalchemy import Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base
from app.common.enums import TargetType


class ProfileScope(Base):
    __tablename__ = "profile_scope"
    __table_args__ = (
        UniqueConstraint("profile_id", "target_type", "target_id"),
        Index("ix_profile_scope_profile_id", "profile_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(TargetType)
    target_id: Mapped[int] = mapped_column(Integer, default=0)
