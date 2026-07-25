from datetime import datetime

from app.common.enums import Permission
from app.common.schemas import CamelModel


class UserCreate(CamelModel):
    email: str
    name: str
    permissions: frozenset[Permission] = frozenset({"viewer"})


class UserUpdate(CamelModel):
    email: str | None = None
    name: str | None = None
    permissions: frozenset[Permission] | None = None


class UserResponse(CamelModel):
    id: int
    email: str
    name: str
    permissions: frozenset[Permission]
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
