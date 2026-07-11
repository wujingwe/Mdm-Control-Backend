from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProfileScope(Base):
    __tablename__ = "profile_scope"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"))
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
