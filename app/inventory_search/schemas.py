from datetime import datetime

from pydantic import BaseModel

from app.criteria.schemas import Criteria


class InventorySearchCreate(BaseModel):
    name: str
    description: str | None = None
    criteria: list[Criteria] = []
    created_by: int


class InventorySearchUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    criteria: list[Criteria] | None = None


class InventorySearchResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    criteria: list[Criteria] = []
    created_at: datetime
    created_by: int
    updated_at: datetime

    model_config = {"from_attributes": True}
