from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Integer, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.core.base import Base, utcnow
from app.infra.criteria.schemas import Criteria
from app.domains.users.models import User


class SmartGroup(Base):
    __tablename__ = "smart_groups"
    __table_args__ = (Index("ix_smart_groups_created_by", "created_by"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    criteria: Mapped[list[Criteria]] = mapped_column(JSON)

    creator: Mapped[User] = relationship(User, foreign_keys=[created_by])
