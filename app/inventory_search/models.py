from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base, utcnow


class InventorySearch(Base):
    __tablename__ = "inventory_searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
