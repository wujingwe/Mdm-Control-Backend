from datetime import datetime

from pydantic import BaseModel, ConfigDict


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


class UserCreateDB(BaseModel):
    email: str
    name: str
    password_hash: str
    permissions: frozenset[str] = frozenset({"viewer"})


class UserUpdateDB(BaseModel):
    email: str | None = None
    name: str | None = None
    password_hash: str | None = None
    permissions: frozenset[str] | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    permissions: frozenset[str]
    created_at: datetime
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
