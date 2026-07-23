from sqlalchemy import select
from sqlalchemy.dialects import mysql

from app.criteria import build_device_query
from app.criteria.schemas import Criteria
from app.devices.models import Device
from app.common.enums import CriteriaType

_mariadb_dialect = mysql.dialect()


def _compile(expr):  # type: ignore[no-untyped-def]
    """Compile a SQLAlchemy expression using MariaDB dialect."""
    return str(expr.compile(compile_kwargs={"literal_binds": True}, dialect=_mariadb_dialect))


def _full_query(expr):  # type: ignore[no-untyped-def]
    """Compile a full SELECT ... WHERE statement using MariaDB dialect."""
    stmt = select(Device).where(expr)
    return str(stmt.compile(compile_kwargs={"literal_binds": True}, dialect=_mariadb_dialect))


# ---------------------------------------------------------------------------
# Empty / invalid input
# ---------------------------------------------------------------------------


class TestEmptyInput:
    def test_empty_criteria_returns_none(self) -> None:
        assert build_device_query([]) is None

    def test_all_invalid_fields_returns_none(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="nonexistent_field",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="test",
                ),
            ]
        )
        assert result is None

    def test_all_invalid_operators_returns_none(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="invalid_op",
                    type=CriteriaType.STRING,
                    value="test",
                ),
            ]
        )
        assert result is None

    def test_mixed_valid_invalid_keeps_valid(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="nonexistent_field",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="skip_me",
                ),
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="keep_me",
                ),
            ]
        )
        assert result is not None
        assert "keep_me" in _compile(result)


# ---------------------------------------------------------------------------
# Single criterion — each operator
# ---------------------------------------------------------------------------


class TestSingleCriterion:
    def test_is_operator(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="Mac")])
        sql = _compile(result)
        assert "devices.name = 'Mac'" in sql

    def test_is_not_operator(self) -> None:
        result = build_device_query([Criteria(field="name", operator="isNot", type=CriteriaType.STRING, value="Mac")])
        sql = _compile(result)
        assert "devices.name != 'Mac'" in sql

    def test_like_operator(self) -> None:
        result = build_device_query([Criteria(field="name", operator="like", type=CriteriaType.STRING, value="Mac")])
        sql = _full_query(result)
        assert "LIKE" in sql
        assert "%Mac%" in sql

    def test_not_like_operator(self) -> None:
        result = build_device_query([Criteria(field="name", operator="notLike", type=CriteriaType.STRING, value="Mac")])
        sql = _full_query(result)
        assert "NOT LIKE" in sql

    def test_matches_regex_operator(self) -> None:
        result = build_device_query(
            [Criteria(field="name", operator="matchesRegex", type=CriteriaType.STRING, value="^Mac")]
        )
        sql = _compile(result)
        assert "devices.name REGEXP '^Mac'" in sql

    def test_does_not_match_regex_operator(self) -> None:
        result = build_device_query(
            [Criteria(field="name", operator="doesNotMatchRegex", type=CriteriaType.STRING, value="^Mac")]
        )
        sql = _compile(result)
        assert "REGEXP" in sql
        assert "NOT" in sql

    def test_greater_than_operator(self) -> None:
        result = build_device_query(
            [Criteria(field="battery_status", operator="greaterThan", type=CriteriaType.NUMBER, value="50")]
        )
        sql = _compile(result)
        assert "devices.battery_status > '50'" in sql

    def test_greater_than_or_equal_operator(self) -> None:
        result = build_device_query(
            [Criteria(field="battery_status", operator="greaterThanOrEqual", type=CriteriaType.NUMBER, value="50")]
        )
        sql = _compile(result)
        assert "devices.battery_status >= '50'" in sql

    def test_less_than_operator(self) -> None:
        result = build_device_query(
            [Criteria(field="battery_status", operator="lessThan", type=CriteriaType.NUMBER, value="30")]
        )
        sql = _compile(result)
        assert "devices.battery_status < '30'" in sql

    def test_less_than_or_equal_operator(self) -> None:
        result = build_device_query(
            [Criteria(field="battery_status", operator="lessThanOrEqual", type=CriteriaType.NUMBER, value="30")]
        )
        sql = _compile(result)
        assert "devices.battery_status <= '30'" in sql

    def test_numeric_comparison_includes_null_check(self) -> None:
        """greaterThan / lessThan add IS NOT NULL guard."""
        result = build_device_query(
            [Criteria(field="battery_status", operator="greaterThan", type=CriteriaType.NUMBER, value="50")]
        )
        sql = _compile(result)
        assert "IS NOT NULL" in sql

    def test_full_query_selects_from_devices(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="Mac")])
        sql = _full_query(result)
        assert sql.startswith("SELECT devices.")


# ---------------------------------------------------------------------------
# Multiple criteria — AND / OR conjunctions
# ---------------------------------------------------------------------------


class TestMultipleCriteriaConjunctions:
    def test_two_criteria_and(self) -> None:
        result = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="Mac", and_or="AND"),
                Criteria(field="status", operator="is", type=CriteriaType.STRING, value="ENROLLED"),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'Mac' AND devices.status = 'ENROLLED'" in sql

    def test_two_criteria_or(self) -> None:
        result = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="Mac", and_or="OR"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="iPhone"),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'Mac' OR devices.name = 'iPhone'" in sql

    def test_three_criteria_all_and(self) -> None:
        result = build_device_query(
            [
                Criteria(field="name", operator="like", type=CriteriaType.STRING, value="Mac", and_or="AND"),
                Criteria(field="status", operator="is", type=CriteriaType.STRING, value="ENROLLED", and_or="AND"),
                Criteria(field="os_version", operator="like", type=CriteriaType.STRING, value="macOS"),
            ]
        )
        sql = _full_query(result)
        assert "AND" in sql
        assert "%Mac%" in sql
        assert "ENROLLED" in sql
        assert "%macOS%" in sql

    def test_three_criteria_mixed_and_or(self) -> None:
        """A AND B OR C — OR connects the last criterion."""
        result = build_device_query(
            [
                Criteria(field="name", operator="like", type=CriteriaType.STRING, value="Mac", and_or="AND"),
                Criteria(field="status", operator="is", type=CriteriaType.STRING, value="ENROLLED", and_or="OR"),
                Criteria(field="os_version", operator="like", type=CriteriaType.STRING, value="iOS"),
            ]
        )
        sql = _full_query(result)
        assert "AND" in sql
        assert "OR" in sql

    def test_and_is_case_insensitive(self) -> None:
        result_lower = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="a", and_or="and"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="b"),
            ]
        )
        result_upper = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="a", and_or="AND"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="b"),
            ]
        )
        assert _compile(result_lower) == _compile(result_upper)

    def test_or_is_case_insensitive(self) -> None:
        result_lower = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="a", and_or="or"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="b"),
            ]
        )
        result_upper = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="a", and_or="OR"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="b"),
            ]
        )
        assert _compile(result_lower) == _compile(result_upper)


# ---------------------------------------------------------------------------
# Parentheses grouping
# ---------------------------------------------------------------------------


class TestParenthesesGrouping:
    def test_single_parenthesized_group(self) -> None:
        """(A AND B) — single group, no parentheses needed in output."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="Mac",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="ENROLLED",
                    and_or="AND",
                    right_parentheses=True,
                ),
            ]
        )
        sql = _full_query(result)
        assert "%Mac%" in sql
        assert "ENROLLED" in sql
        assert "AND" in sql

    def test_two_groups_and(self) -> None:
        """(A AND B) AND (C AND D) — AND is associative, no parentheses needed."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="Mac",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="ENROLLED",
                    and_or="AND",
                    right_parentheses=True,
                ),
                Criteria(
                    field="os_version",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="macOS",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="connection_status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="CONNECTED",
                    and_or="AND",
                    right_parentheses=True,
                ),
            ]
        )
        sql = _full_query(result)
        assert "%Mac%" in sql
        assert "ENROLLED" in sql
        assert "%macOS%" in sql
        assert "CONNECTED" in sql
        assert sql.count("AND") >= 3

    def test_two_groups_or(self) -> None:
        """(A AND B) OR (C AND D) — conjunction between groups from last criterion of group 0."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="Mac",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="ENROLLED",
                    and_or="OR",
                    right_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="iPhone",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="PENDING",
                    and_or="AND",
                    right_parentheses=True,
                ),
            ]
        )
        sql = _full_query(result)
        assert "%Mac%" in sql
        assert "%iPhone%" in sql
        assert "ENROLLED" in sql
        assert "PENDING" in sql

    def test_three_groups(self) -> None:
        """(A) AND (B) AND (C)"""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="Mac",
                    and_or="AND",
                    left_parentheses=True,
                    right_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="iPhone",
                    and_or="AND",
                    left_parentheses=True,
                    right_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="Galaxy",
                    and_or="AND",
                    left_parentheses=True,
                    right_parentheses=True,
                ),
            ]
        )
        sql = _full_query(result)
        assert "%Mac%" in sql
        assert "%iPhone%" in sql
        assert "%Galaxy%" in sql
        assert sql.count("AND") >= 2

    def test_parentheses_override_precedence(self) -> None:
        """(A OR B) AND C — parentheses force OR to evaluate first."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="Mac",
                    and_or="OR",
                    left_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="iPhone",
                    and_or="AND",
                    right_parentheses=True,
                ),
                Criteria(
                    field="status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="ENROLLED",
                ),
            ]
        )
        sql = _compile(result)
        assert "(devices.name LIKE" in sql
        assert "OR devices.name LIKE" in sql
        assert "devices.status = 'ENROLLED'" in sql

    def test_left_parentheses_resets_group(self) -> None:
        """Multiple left_parentheses should start fresh groups."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="A",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="B",
                    and_or="AND",
                    right_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="C",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="D",
                    and_or="AND",
                    right_parentheses=True,
                ),
            ]
        )
        sql = _compile(result)
        assert "%A%" in sql
        assert "%B%" in sql
        assert "%C%" in sql
        assert "%D%" in sql

    def test_open_parentheses_without_close_groups_at_end(self) -> None:
        """If right_parentheses is never set, remaining criteria form a final group."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="A",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="B",
                ),
            ]
        )
        sql = _compile(result)
        assert "%A%" in sql
        assert "%B%" in sql


# ---------------------------------------------------------------------------
# Edge cases with invalid fields / operators mixed in
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_invalid_field_between_valid_skips_it(self) -> None:
        result = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A", and_or="AND"),
                Criteria(field="no_such_col", operator="is", type=CriteriaType.STRING, value="B", and_or="AND"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="C"),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'A'" in sql
        assert "devices.name = 'C'" in sql
        assert "'B'" not in sql

    def test_invalid_operator_between_valid_skips_it(self) -> None:
        result = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A", and_or="AND"),
                Criteria(field="name", operator="bogus_op", type=CriteriaType.STRING, value="B", and_or="AND"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="C"),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'A'" in sql
        assert "devices.name = 'C'" in sql
        assert "'B'" not in sql

    def test_empty_string_value(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="")])
        sql = _compile(result)
        assert "devices.name = ''" in sql

    def test_single_criterion_with_parentheses(self) -> None:
        """A single criterion with both left and right parentheses."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="Mac",
                    left_parentheses=True,
                    right_parentheses=True,
                ),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'Mac'" in sql

    def test_only_left_parentheses_criteria(self) -> None:
        """All criteria have left_parentheses but none have right — each starts a new group."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="A",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="B",
                    and_or="AND",
                    left_parentheses=True,
                ),
            ]
        )
        sql = _compile(result)
        assert "'A'" in sql
        assert "'B'" in sql
        assert "AND" in sql

    def test_parentheses_only_on_some_criteria(self) -> None:
        """Only some criteria have parentheses, others are ungrouped."""
        result = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"),
                Criteria(
                    field="status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="ENROLLED",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="os_version",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="iOS",
                    and_or="AND",
                    right_parentheses=True,
                ),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'A'" in sql
        assert "devices.status = 'ENROLLED'" in sql
        assert "devices.os_version = 'iOS'" in sql

    def test_date_value_comparison(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="last_enrolled_at", operator="greaterThanOrEqual", type=CriteriaType.DATE, value="2024-01-01"
                )
            ]
        )
        sql = _compile(result)
        assert "2024-01-01" in sql
        assert "IS NOT NULL" in sql


# ---------------------------------------------------------------------------
# MariaDB SQL validity
# ---------------------------------------------------------------------------


class TestMariaDBValidity:
    def test_select_from_devices_table(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="test")])
        sql = _full_query(result)
        assert "FROM devices" in sql

    def test_table_qualified_column_names(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="test")])
        sql = _compile(result)
        assert "devices.name" in sql

    def test_string_values_single_quoted(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="hello")])
        sql = _compile(result)
        assert "'hello'" in sql

    def test_regex_operator_mariadb_compatible(self) -> None:
        result = build_device_query(
            [Criteria(field="name", operator="matchesRegex", type=CriteriaType.STRING, value="^[A-Z]")]
        )
        sql = _compile(result)
        assert "REGEXP" in sql

    def test_not_regex_operator_mariadb_compatible(self) -> None:
        result = build_device_query(
            [Criteria(field="name", operator="doesNotMatchRegex", type=CriteriaType.STRING, value="^[A-Z]")]
        )
        sql = _compile(result)
        assert "NOT" in sql
        assert "REGEXP" in sql

    def test_parentheses_group_sql_valid(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="Mac",
                    and_or="OR",
                    left_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="iPhone",
                    and_or="AND",
                    right_parentheses=True,
                ),
                Criteria(
                    field="status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="ENROLLED",
                ),
            ]
        )
        sql = _compile(result)
        assert sql.count("(") == sql.count(")")

    def test_complex_query_balanced_parentheses(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="A",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="B",
                    and_or="OR",
                    right_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="C",
                    and_or="AND",
                    left_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="D",
                    and_or="AND",
                    right_parentheses=True,
                ),
            ]
        )
        sql = _compile(result)
        assert sql.count("(") == sql.count(")")


# ---------------------------------------------------------------------------
# _build_filter unit tests
# ---------------------------------------------------------------------------


class TestBuildFilter:
    def test_valid_field_and_operator(self) -> None:
        from app.criteria import _build_filter

        c = Criteria(field="name", operator="is", type=CriteriaType.STRING, value="test")
        result = _build_filter(c)
        assert result is not None

    def test_invalid_field_returns_none(self) -> None:
        from app.criteria import _build_filter

        c = Criteria(field="nonexistent", operator="is", type=CriteriaType.STRING, value="test")
        assert _build_filter(c) is None

    def test_invalid_operator_returns_none(self) -> None:
        from app.criteria import _build_filter

        c = Criteria(field="name", operator="bogus", type=CriteriaType.STRING, value="test")
        assert _build_filter(c) is None


# ---------------------------------------------------------------------------
# _combine unit tests
# ---------------------------------------------------------------------------


class TestCombine:
    def test_and_combination(self) -> None:
        from app.criteria import _build_filter, _combine

        left = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"))
        right = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B"))
        result = _combine(left, "AND", right)  # type: ignore[arg-type]
        sql = _compile(result)
        assert "AND" in sql

    def test_or_combination(self) -> None:
        from app.criteria import _build_filter, _combine

        left = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"))
        right = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B"))
        result = _combine(left, "OR", right)  # type: ignore[arg-type]
        sql = _compile(result)
        assert "OR" in sql

    def test_and_is_case_insensitive(self) -> None:
        from app.criteria import _build_filter, _combine

        left = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"))
        right = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B"))
        result_lower = _combine(left, "and", right)  # type: ignore[arg-type]
        result_upper = _combine(left, "AND", right)  # type: ignore[arg-type]
        assert _compile(result_lower) == _compile(result_upper)
