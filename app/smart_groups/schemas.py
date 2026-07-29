from datetime import datetime

from pydantic import Field, model_validator

from app.common.schemas import CamelModel
from app.criteria.schemas import Criteria, VALID_CRITERIA_FIELDS


class SmartGroupCreate(CamelModel):
    name: str
    description: str | None = None
    criteria: list[Criteria] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_criteria_fields(self) -> "SmartGroupCreate":
        for c in self.criteria:
            if c.extension_attribute_id is not None:
                continue
            if c.field not in VALID_CRITERIA_FIELDS:
                raise ValueError(f"Unknown criteria field: {c.field}")
        return self


class SmartGroupUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    criteria: list[Criteria] | None = None

    @model_validator(mode="after")
    def _validate_criteria_fields(self) -> "SmartGroupUpdate":
        if self.criteria is not None:
            for c in self.criteria:
                if c.extension_attribute_id is not None:
                    continue
                if c.field not in VALID_CRITERIA_FIELDS:
                    raise ValueError(f"Unknown criteria field: {c.field}")
        return self


class SmartGroupResponse(CamelModel):
    id: int
    name: str
    description: str | None = None
    criteria: list[Criteria]
    created_by: int
    created_at: datetime
    updated_at: datetime
