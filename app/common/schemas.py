from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class Message(BaseModel):
    detail: str


class PaginatedResponse(CamelModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


class ScopeType(str, Enum):
    ALL_DEVICES = "ALL_DEVICES"
    SMART_GROUP = "SMART_GROUP"
    STATIC_GROUP = "STATIC_GROUP"
    DEVICE = "DEVICE"


class ScopeTarget(CamelModel):
    scope_type: ScopeType
    target_id: int | None = None


class ScopeExclusion(CamelModel):
    scope_type: ScopeType
    exclude_id: int | None = None


class Scope(CamelModel):
    targets: list[ScopeTarget] = []
    exclusions: list[ScopeExclusion] = []
