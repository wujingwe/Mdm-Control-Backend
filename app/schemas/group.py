from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import CriteriaSchema


class GroupCreate(BaseModel):
    name: str
    description: str | None = None
    criteria: dict[str, Any] | None = None
    display_columns: list[str] | None = None
    is_smart: bool = False
    created_by: int = 1


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    criteria: dict[str, Any] | None = None
    display_columns: list[str] | None = None
    is_smart: bool | None = None


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    criteria: dict[str, Any] | None = None
    display_columns: list[str] | None = None
    is_smart: bool = False
    created_by: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SmartGroupCreate(BaseModel):
    name: str
    description: str | None = None
    criteria: list[CriteriaSchema] = []
    created_by: int = 1


class SmartGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    criteria: list[CriteriaSchema] | None = None


class SmartGroupResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    criteria: list[CriteriaSchema] | None = None
    created_at: datetime
    created_by: int
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
