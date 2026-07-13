from datetime import datetime
from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    permissions: frozenset[str] = frozenset({"viewer"})


class UserUpdate(BaseModel):
    email: str | None = None
    name: str | None = None
    password: str | None = None
    permissions: frozenset[str] | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    permissions: frozenset[str]
    created_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}
