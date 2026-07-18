from collections.abc import Callable
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
    criteria: list[Criteria],
) -> tuple[BinaryExpression | None, list[BinaryExpression]]:
    """Build a SQLAlchemy WHERE expression from a list of Criteria.

    Each criterion's ``and_or`` field determines the conjunction to the
    *next* criterion (AND / OR).  ``left_parentheses`` / ``right_parentheses``
    group criteria into sub-expressions so that parentheses override the
    default left-to-right evaluation.

    Returns ``(where_expression, all_filters)``.
    """
    from app.devices.models import Device

    # 1. Build individual column filters
    filters: list[BinaryExpression | None] = []
    for c in criteria:
        col = getattr(Device, c.field, None)
        if col is None:
            filters.append(None)
            continue
        builder = FILTER_BUILDERS.get(c.operator)
        filters.append(builder(col, c.value) if builder else None)

    # 2. Group consecutive criteria by parentheses.
    #    A ``left_parentheses`` starts a new group; a ``right_parentheses``
    #    closes the current group.  Criteria without any parentheses land in
    #    a single implicit group.
    groups: list[list[tuple[BinaryExpression, str]]] = []
    current_group: list[tuple[BinaryExpression, str]] = []

    for i, c in enumerate(criteria):
        f = filters[i]
        if f is None:
            continue

        if c.left_parentheses:
            current_group = []

        current_group.append((f, c.and_or))

        if c.right_parentheses:
            groups.append(current_group)
            current_group = []

    if current_group:
        groups.append(current_group)

    if not groups:
        return None, []

    # 3. Within each group, combine filters using the conjunction stored on
    #    each criterion (except the last, whose ``and_or`` connects to the
    #    next group).
    group_exprs: list[BinaryExpression] = []
    group_conjs: list[str] = []

    for group in groups:
        expr = group[0][0]
        for j in range(1, len(group)):
            conj = group[j - 1][1]
            combine = and_ if conj.upper() == "AND" else or_
            expr = combine(expr, group[j][0])
        group_exprs.append(expr)
        group_conjs.append(group[-1][1])

    # 4. Combine groups.  The conjunction between group *i-1* and group *i*
    #    is the ``and_or`` of the last criterion in group *i-1*.
    result = group_exprs[0]
    for idx in range(1, len(group_exprs)):
        conj = group_conjs[idx - 1]
        combine = and_ if conj.upper() == "AND" else or_
        result = combine(result, group_exprs[idx])

    all_filters = [f for f in filters if f is not None]
    return result, all_filters
