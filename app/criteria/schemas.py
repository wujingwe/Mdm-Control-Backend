from pydantic import BaseModel

from app.common.enums import CriteriaType


class Criteria(BaseModel):
    field: str
    operator: str
    type: CriteriaType
    value: str
    left_parentheses: bool = False
    right_parentheses: bool = False
