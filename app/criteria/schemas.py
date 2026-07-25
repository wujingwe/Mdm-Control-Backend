from app.common.enums import CriteriaType
from app.common.schemas import CamelModel


class Criteria(CamelModel):
    field: str
    operator: str
    type: CriteriaType
    value: str
    and_or: str = "AND"
    left_parentheses: bool = False
    right_parentheses: bool = False
