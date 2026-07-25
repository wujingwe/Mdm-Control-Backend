from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    DateTime,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.criteria.schemas import Criteria
from app.users.models import User


class InventorySearch(Base):
    __tablename__ = "inventory_searches"
    __table_args__ = (
        UniqueConstraint("name"),
        Index("ix_inventory_searches_created_by", "created_by"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria: Mapped[list[Criteria]] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    creator: Mapped[User] = relationship(User, foreign_keys=[created_by])
