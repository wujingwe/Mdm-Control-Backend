from datetime import datetime
from enum import Enum

from pydantic import BaseModel


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


class InventorySearchCreate(BaseModel):
    name: str
    description: str | None = None
    criteria: list[CriteriaSchema] = []
    created_by: int


class InventorySearchUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    criteria: list[CriteriaSchema] | None = None


class InventorySearchResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    criteria: list[CriteriaSchema] = []
    created_at: datetime
    created_by: int
    updated_at: datetime

    model_config = {"from_attributes": True}
