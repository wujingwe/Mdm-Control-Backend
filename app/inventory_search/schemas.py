from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.criteria.schemas import Criteria


class InventorySearchCreate(BaseModel):
    name: str
    description: str | None = None
    criteria: list[Criteria] = Field(min_length=1)
    created_by: int


class InventorySearchUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    criteria: list[Criteria] | None = None

    @model_validator(mode="after")
    def _validate_criteria(self) -> "InventorySearchUpdate":
        if self.criteria is not None and len(self.criteria) == 0:
            raise ValueError("criteria must not be empty when provided")
        return self


class InventorySearchResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    criteria: list[Criteria] = []
    created_at: datetime
    created_by: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventorySearchExecuteRequest(BaseModel):
    criteria: list[Criteria] = Field(min_length=1)
