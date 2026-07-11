from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class CriteriaType(str, Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    date = "date"


class CriteriaSchema(BaseModel):
    criteria: str
    operator: str
    type: CriteriaType
    value: str
    left_parentheses: bool = False
    right_parentheses: bool = False


class Message(BaseModel):
    detail: str


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int
