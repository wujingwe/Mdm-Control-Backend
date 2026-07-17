from datetime import datetime

from pydantic import BaseModel

from app.criteria.schemas import Criteria


class SmartGroupCreate(BaseModel):
    name: str
    description: str | None = None
    criteria: list[Criteria] = []
    created_by: int = 1


class SmartGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    criteria: list[Criteria] | None = None


class SmartGroupResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    criteria: list[Criteria] | None = None
    created_at: datetime
    created_by: int
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
