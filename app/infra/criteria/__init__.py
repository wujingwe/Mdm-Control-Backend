from collections.abc import Callable
from itertools import pairwise

from sqlalchemy import select
from sqlalchemy.sql.expression import ColumnElement

from app.infra.criteria.schemas import Criteria
from app.domains.devices.models import Device, DeviceExtensionAttributeValue

__all__ = ["Criteria", "FILTER_BUILDERS", "build_device_query"]

FILTER_BUILDERS: dict[str, Callable[..., ColumnElement[bool]]] = {
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


def _build_ext_attr_filter(c: Criteria) -> ColumnElement[bool] | None:
    """Build an EXISTS subquery filter for an extension attribute criterion."""
    builder = FILTER_BUILDERS.get(c.operator)
    if builder is None:
        return None
    value_expr = builder(DeviceExtensionAttributeValue.value, c.value)
    return (
        select(DeviceExtensionAttributeValue.device_id)
        .where(
            DeviceExtensionAttributeValue.extension_attribute_id == c.extension_attribute_id,
            DeviceExtensionAttributeValue.device_id == Device.id,
            value_expr,
        )
        .exists()
    )


def _build_filter(c: Criteria) -> ColumnElement[bool] | None:
    """Build a single filter expression from a Criterion."""
    col = getattr(Device, c.field, None)
    if c.extension_attribute_id is not None:
        return _build_ext_attr_filter(c)
    if col is None:
        return None
    builder = FILTER_BUILDERS.get(c.operator)
    return builder(col, c.value) if builder else None


def _combine(left: ColumnElement[bool], conj: str, right: ColumnElement[bool]) -> ColumnElement[bool]:
    """Combine two expressions using the given conjunction."""
    return left & right if conj.upper() == "AND" else left | right


def _partition(criteria: list[Criteria]) -> list[list[tuple[ColumnElement[bool], str]]]:
    """Split criteria into parenthesized groups, each entry ``(expr, and_or)``."""
    groups: list[list[tuple[ColumnElement[bool], str]]] = []
    current: list[tuple[ColumnElement[bool], str]] = []

    for c in criteria:
        expr = _build_filter(c)
        if expr is None:
            continue
        if c.left_parentheses and current:
            groups.append(current)
            current = []
        current.append((expr, c.and_or))
        if c.right_parentheses:
            groups.append(current)
            current = []

    if current:
        groups.append(current)
    return groups


def _fold_group(group: list[tuple[ColumnElement[bool], str]]) -> tuple[ColumnElement[bool], str]:
    """Fold a group into a single expression, returning ``(expr, trailing_conj)``.

    ``trailing_conj`` is the ``and_or`` of the last criterion, which connects
    this group to the next one.
    """
    expr = group[0][0]
    for (left_expr, conj), (right_expr, _) in pairwise(group):
        expr = _combine(expr, conj, right_expr)
    return expr, group[-1][1]


def build_device_query(
    criteria: list[Criteria],
) -> ColumnElement[bool] | None:
    """Build a SQLAlchemy WHERE expression from a list of Criteria.

    Each criterion's ``and_or`` field determines the conjunction to the
    *next* criterion (AND / OR).  ``left_parentheses`` / ``right_parentheses``
    group criteria into sub-expressions so that parentheses override the
    default left-to-right evaluation.
    """
    groups = [_fold_group(group) for group in _partition(criteria)]
    if not groups:
        return None

    result, _ = groups[0]
    for (left_expr, conj), (right_expr, _) in pairwise(groups):
        result = _combine(result, conj, right_expr)
    return result
