from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.base import Base, utcnow
from app.common.enums import ExtensionDataType, ExtensionInputType
from app.users.models import User


class ExtensionAttribute(Base):
    __tablename__ = "extension_attributes"
    __table_args__ = (Index("ix_extension_attributes_created_by", "created_by"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(Enum(ExtensionDataType, native_enum=False, length=20))
    input_type: Mapped[str] = mapped_column(Enum(ExtensionInputType, native_enum=False, length=20))
    popup_choices: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    creator: Mapped[User] = relationship(User, foreign_keys=[created_by])
