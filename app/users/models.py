from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.base import Base, utcnow
from app.types import PermissionListType

if TYPE_CHECKING:
    from app.smart_groups.models import SmartGroup
    from app.static_groups.models import StaticGroup
    from app.profiles.models import Profile
    from app.extension_attributes.models import ExtensionAttribute
    from app.inventory_search.models import InventorySearch


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    permissions: Mapped[frozenset[str]] = mapped_column(PermissionListType, default=lambda: frozenset({"viewer"}))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    smart_groups: Mapped[list[SmartGroup]] = relationship(back_populates="creator")
    static_groups: Mapped[list[StaticGroup]] = relationship(back_populates="creator")
    profiles: Mapped[list[Profile]] = relationship(back_populates="creator")
    extension_attributes: Mapped[list[ExtensionAttribute]] = relationship(back_populates="creator")
    inventory_searches: Mapped[list[InventorySearch]] = relationship(back_populates="creator")
