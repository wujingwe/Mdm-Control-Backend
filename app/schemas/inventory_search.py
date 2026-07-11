from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import CriteriaSchema


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
