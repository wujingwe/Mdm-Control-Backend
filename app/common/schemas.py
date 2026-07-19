from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Message(BaseModel):
    detail: str


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


class ScopeType(str, Enum):
    ALL_DEVICES = "ALL_DEVICES"
    SMART_GROUP = "SMART_GROUP"
    STATIC_GROUP = "STATIC_GROUP"
    DEVICE = "DEVICE"


class Target(BaseModel):
    scope_type: ScopeType
    target_id: int | None = None


class Exclusion(BaseModel):
    scope_type: ScopeType
    exclude_id: int | None = None


class Scope(BaseModel):
    targets: list[Target] = []
    exclusions: list[Exclusion] = []
