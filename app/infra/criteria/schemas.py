from app.domains.devices.criteria import CriteriaType
from app.infra.common.schemas import CamelModel

VALID_CRITERIA_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "serial_number",
        "os_version",
        "connection_status",
        "status",
        "battery_status",
        "total_storage",
        "available_storage",
        "total_memory",
        "available_memory",
        "last_enrolled_at",
        "created_at",
        "updated_at",
    }
)


class Criteria(CamelModel):
    field: str
    operator: str
    type: CriteriaType
    value: str
    and_or: str = "AND"
    left_parentheses: bool = False
    right_parentheses: bool = False
    extension_attribute_id: int | None = None
