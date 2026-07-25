from datetime import datetime

from pydantic import Field, model_validator

from app.common.schemas import CamelModel
from app.criteria.schemas import Criteria


class InventorySearchCreate(CamelModel):
    name: str
    description: str | None = None
    criteria: list[Criteria] = Field(min_length=1)


class InventorySearchUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    criteria: list[Criteria] | None = None

    @model_validator(mode="after")
    def _validate_criteria(self) -> "InventorySearchUpdate":
        if self.criteria is not None and len(self.criteria) == 0:
            raise ValueError("criteria must not be empty when provided")
        return self


class InventorySearchResponse(CamelModel):
    id: int
    name: str
    description: str | None = None
    criteria: list[Criteria] = []
    created_by: int
    created_at: datetime
    updated_at: datetime


class InventorySearchExecuteRequest(CamelModel):
    criteria: list[Criteria] = Field(min_length=1)
