from collections.abc import Callable
from functools import reduce
from operator import and_, or_

from sqlalchemy.sql.expression import BinaryExpression

from app.criteria.schemas import Criteria

__all__ = ["Criteria", "FILTER_BUILDERS", "build_device_query"]

FILTER_BUILDERS: dict[str, Callable] = {
    "is": lambda col, v: col == v,
    "isNot": lambda col, v: col != v,
    "like": lambda col, v: col.like(f"%{v}%"),
    "notLike": lambda col, v: col.not_like(f"%{v}%"),
    "matchesRegex": lambda col, v: col.regexp_match(v),
    "doesNotMatchRegex": lambda col, v: ~col.regexp_match(v),
    "greaterThan": lambda col, v: col.isnot(None) & (col > v),
    "greaterThanOrEqual": lambda col, v: col.isnot(None) & (col >= v),
    "lessThan": lambda col, v: col.isnot(None) & (col < v),
    "lessThanOrEqual": lambda col, v: col.isnot(None) & (col <= v),
}


def build_device_query(
    criteria: list[Criteria], conjunction: str = "AND"
) -> tuple[BinaryExpression | None, list[BinaryExpression]]:
    from app.devices.models import Device

    filters: list[BinaryExpression] = []

    for c in criteria:
        col = getattr(Device, c.field, None)
        if col is None:
            continue
        builder = FILTER_BUILDERS.get(c.operator)
        if builder is not None:
            filters.append(builder(col, c.value))

    where = None
    if filters:
        combine = and_ if conjunction.upper() == "AND" else or_
        where = reduce(combine, filters)

    return where, filters
