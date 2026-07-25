from datetime import datetime

from pydantic import Field

from app.common.schemas import CamelModel
from app.criteria.schemas import Criteria


class SmartGroupCreate(CamelModel):
    name: str
    description: str | None = None
    criteria: list[Criteria] = Field(min_length=1)


class SmartGroupUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    criteria: list[Criteria] | None = None


class SmartGroupResponse(CamelModel):
    id: int
    name: str
    description: str | None = None
    criteria: list[Criteria]
    created_by: int
    created_at: datetime
    updated_at: datetime
