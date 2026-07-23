from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base, utcnow
from app.common.schemas import Scope
from app.profiles.models import ScopeColumnType


class MobileApp(Base):
    __tablename__ = "mobile_apps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[str] = mapped_column(String(32))
    package_name: Mapped[str] = mapped_column(String(64))
    scope: Mapped[Scope] = mapped_column(ScopeColumnType)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
