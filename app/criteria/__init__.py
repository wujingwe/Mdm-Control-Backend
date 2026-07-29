from collections.abc import Callable
from operator import and_, or_

from sqlalchemy import select
from sqlalchemy.sql.expression import BinaryExpression

from app.criteria.schemas import Criteria
from app.devices.models import Devicefrom app.devices.models import Device, DeviceExtensionAttributeValue

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


def _build_ext_attr_filter(c: Criteria) -> BinaryExpression | None:
    """Build an EXISTS subquery filter for an extension attribute criterion."""
    builder = FILTER_BUILDERS.get(c.operator)
    if builder is None:
        return None
    value_expr = builder(DeviceExtensionAttributeValue.value, c.value)
    subq = (
        select(DeviceExtensionAttributeValue.device_id)
        .where(
            DeviceExtensionAttributeValue.extension_attribute_id == c.extension_attribute_id,
            DeviceExtensionAttributeValue.device_id == Device.id,
            value_expr,
        )
        .exists()
    )
    return subq

        
def _build_filter(c: Criteria) -> BinaryExpression | None:
    """Build a single filter expression from a Criterion."""
    col = getattr(Device, c.field, None)
    if c.extension_attribute_id is not None:
        return _build_ext_attr_filter(c)
    builder = FILTER_BUILDERS.get(c.operator)
    return builder(col, c.value) if builder else None


def _combine(left: BinaryExpression, conj: str, right: BinaryExpression) -> BinaryExpression:
    """Combine two expressions using the given conjunction."""
    fn = and_ if conj.upper() == "AND" else or_
    result: BinaryExpression = fn(left, right)
    return result


def build_device_query(
    criteria: list[Criteria],
) -> BinaryExpression | None:
    """Build a SQLAlchemy WHERE expression from a list of Criteria.

    Each criterion's ``and_or`` field determines the conjunction to the
    *next* criterion (AND / OR).  ``left_parentheses`` / ``right_parentheses``
    group criteria into sub-expressions so that parentheses override the
    default left-to-right evaluation.
    """

    # 1. Group consecutive criteria by parentheses.
    groups: list[list[tuple[BinaryExpression, str]]] = []
    current_group: list[tuple[BinaryExpression, str]] = []

    for c in criteria:
        f = _build_filter(c)
        if f is None:
            continue
        if c.left_parentheses:
            if current_group:
                groups.append(current_group)
            current_group = []
        current_group.append((f, c.and_or))
        if c.right_parentheses:
            groups.append(current_group)
            current_group = []

    if current_group:
        groups.append(current_group)

    if not groups:
        return None

    # 2. Combine each group using the conjunction on each criterion.
    group_exprs: list[BinaryExpression] = []
    group_conjs: list[str] = []

    for group in groups:
        expr = group[0][0]
        for j in range(1, len(group)):
            expr = _combine(expr, group[j - 1][1], group[j][0])
        group_exprs.append(expr)
        group_conjs.append(group[-1][1])

    # 3. Combine groups.  The conjunction between group i-1 and group i
    #    is the ``and_or`` of the last criterion in group i-1.
    result = group_exprs[0]
    for idx in range(1, len(group_exprs)):
        result = _combine(result, group_conjs[idx - 1], group_exprs[idx])

    return result
