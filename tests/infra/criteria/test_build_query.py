import pytest
from sqlalchemy import select, ColumnElement
from sqlalchemy.dialects import mysql

from app.infra.criteria import build_device_query, _build_filter, _combine, _fold_group, _partition
from app.infra.criteria.schemas import VALID_CRITERIA_FIELDS, Criteria
from app.domains.devices.models import Device
from app.domains.devices.criteria import CriteriaType

_mariadb_dialect = mysql.dialect()


def _compile(expr: ColumnElement[bool]):
    """Compile a SQLAlchemy expression using MariaDB dialect."""
    return str(expr.compile(compile_kwargs={"literal_binds": True}, dialect=_mariadb_dialect))


def _full_query(expr: ColumnElement[bool]):
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
        assert "devices.name = 'Mac' AND devices.status = 'ENROLLED'" == sql

    def test_two_criteria_or(self) -> None:
        result = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="Mac", and_or="OR"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="iPhone"),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'Mac' OR devices.name = 'iPhone'" == sql

    def test_three_criteria_all_and(self) -> None:
        result = build_device_query(
            [
                Criteria(field="name", operator="like", type=CriteriaType.STRING, value="Mac", and_or="AND"),
                Criteria(field="status", operator="is", type=CriteriaType.STRING, value="ENROLLED", and_or="AND"),
                Criteria(field="os_version", operator="like", type=CriteriaType.STRING, value="macOS"),
            ]
        )
        sql = _compile(result)
        assert (
            "devices.name LIKE '%%Mac%%' AND devices.status = 'ENROLLED' AND devices.os_version LIKE '%%macOS%%'" == sql
        )

    def test_three_criteria_mixed_and_or(self) -> None:
        """A AND B OR C — OR connects the last criterion."""
        result = build_device_query(
            [
                Criteria(field="name", operator="like", type=CriteriaType.STRING, value="Mac", and_or="AND"),
                Criteria(field="status", operator="is", type=CriteriaType.STRING, value="ENROLLED", and_or="OR"),
                Criteria(field="os_version", operator="like", type=CriteriaType.STRING, value="iOS"),
            ]
        )
        sql = _compile(result)
        assert "devices.name LIKE '%%Mac%%' AND devices.status = 'ENROLLED' OR devices.os_version LIKE '%%iOS%%'" == sql

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
        sql = _compile(result)
        assert "devices.name LIKE '%%Mac%%' AND devices.status = 'ENROLLED'" == sql

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
        sql = _compile(result)
        assert (
            "devices.name LIKE '%%Mac%%' AND devices.status = 'ENROLLED' AND devices.os_version LIKE '%%macOS%%' AND devices.connection_status = 'CONNECTED'"
            == sql
        )
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
        sql = _compile(result)
        assert (
            "devices.name LIKE '%%Mac%%' AND devices.status = 'ENROLLED' OR devices.name LIKE '%%iPhone%%' AND devices.status = 'PENDING'"
            == sql
        )

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
        sql = _compile(result)
        assert (
            "devices.name LIKE '%%Mac%%' AND devices.name LIKE '%%iPhone%%' AND devices.name LIKE '%%Galaxy%%'" == sql
        )
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
        assert "(devices.name LIKE '%%Mac%%' OR devices.name LIKE '%%iPhone%%') AND devices.status = 'ENROLLED'" == sql

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
        assert (
            "devices.name LIKE '%%A%%' AND devices.name LIKE '%%B%%' AND devices.name LIKE '%%C%%' AND devices.name LIKE '%%D%%'"
            == sql
        )

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
        assert "devices.name LIKE '%%A%%' AND devices.name LIKE '%%B%%'" == sql


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
        assert "devices.name = 'A' AND devices.name = 'C'" == sql

    def test_invalid_operator_between_valid_skips_it(self) -> None:
        result = build_device_query(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A", and_or="AND"),
                Criteria(field="name", operator="bogus_op", type=CriteriaType.STRING, value="B", and_or="AND"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="C"),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'A' AND devices.name = 'C'" == sql

    def test_empty_string_value(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="")])
        sql = _compile(result)
        assert "devices.name = ''" == sql

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
        assert "devices.name = 'Mac'" == sql

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
        assert "devices.name = 'A' AND devices.name = 'B'" == sql

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
        assert "devices.name = 'A' AND devices.status = 'ENROLLED' AND devices.os_version = 'iOS'" == sql

    def test_date_value_comparison(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="last_enrolled_at", operator="greaterThanOrEqual", type=CriteriaType.DATE, value="2024-01-01"
                )
            ]
        )
        sql = _compile(result)
        assert "devices.last_enrolled_at IS NOT NULL AND devices.last_enrolled_at >= '2024-01-01'" == sql


# ---------------------------------------------------------------------------
# MariaDB SQL validity
# ---------------------------------------------------------------------------


class TestMariaDBValidity:
    def test_select_from_devices_table(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="test")])
        sql = _compile(result)
        assert "devices.name = 'test'" == sql

    def test_table_qualified_column_names(self) -> None:
        result = build_device_query([Criteria(field="name", operator="is", type=CriteriaType.STRING, value="test")])
        sql = _compile(result)
        assert "devices.name = 'test'" == sql

    def test_regex_operator_mariadb_compatible(self) -> None:
        result = build_device_query(
            [Criteria(field="name", operator="matchesRegex", type=CriteriaType.STRING, value="^[A-Z]")]
        )
        sql = _compile(result)
        assert "devices.name REGEXP '^[A-Z]'" == sql

    def test_not_regex_operator_mariadb_compatible(self) -> None:
        result = build_device_query(
            [Criteria(field="name", operator="doesNotMatchRegex", type=CriteriaType.STRING, value="^[A-Z]")]
        )
        sql = _compile(result)
        assert "devices.name NOT REGEXP '^[A-Z]'" == sql

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
        assert "(devices.name LIKE '%%Mac%%' OR devices.name LIKE '%%iPhone%%') AND devices.status = 'ENROLLED'" == sql
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
        assert (
            "devices.name LIKE '%%A%%' AND devices.name LIKE '%%B%%' OR devices.name LIKE '%%C%%' AND devices.name LIKE '%%D%%'"
            == sql
        )
        assert sql.count("(") == sql.count(")")


# ---------------------------------------------------------------------------
# Extension attribute criteria (EXISTS subquery path)
# ---------------------------------------------------------------------------


class TestExtensionAttributeCriteria:
    def test_is_operator_builds_exists_subquery(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="ignored_field",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="x",
                    extension_attribute_id=42,
                )
            ]
        )
        sql = _compile(result)
        assert (
            "EXISTS (SELECT device_extension_attribute_values.device_id \n"
            "FROM device_extension_attribute_values, devices \n"
            "WHERE device_extension_attribute_values.extension_attribute_id = 42 "
            "AND device_extension_attribute_values.device_id = devices.id "
            "AND device_extension_attribute_values.value = 'x')"
        ) == sql

    def test_ext_attr_subquery_correlates_to_device(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="x",
                    extension_attribute_id=1,
                )
            ]
        )
        sql = _compile(result)
        assert (
            "EXISTS (SELECT device_extension_attribute_values.device_id \n"
            "FROM device_extension_attribute_values, devices \n"
            "WHERE device_extension_attribute_values.extension_attribute_id = 1 AND "
            "device_extension_attribute_values.device_id = devices.id AND "
            "device_extension_attribute_values.value = 'x')"
        ) == sql
        assert "device_extension_attribute_values.device_id = devices.id" in sql

    @pytest.mark.parametrize(
        ("operator", "expected_fragment"),
        [
            ("is", "value = 'x'"),
            ("isNot", "value != 'x'"),
            ("like", "value LIKE '%%x%%'"),
            ("notLike", "value NOT LIKE '%%x%%'"),
            ("matchesRegex", "value REGEXP '^a'"),
            ("doesNotMatchRegex", "value NOT REGEXP '^a'"),
            ("greaterThan", "value > '5'"),
            ("greaterThanOrEqual", "value >= '5'"),
            ("lessThan", "value < '5'"),
            ("lessThanOrEqual", "value <= '5'"),
        ],
    )
    def test_all_operators_apply_to_value_column(self, operator: str, expected_fragment: str) -> None:
        value = "5" if "Than" in operator else ("^a" if "Regex" in operator else "x")
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator=operator,
                    type=CriteriaType.STRING,
                    value=value,
                    extension_attribute_id=7,
                )
            ]
        )
        sql = _compile(result)
        assert (
            "EXISTS (SELECT device_extension_attribute_values.device_id \n"
            "FROM device_extension_attribute_values, devices \n"
            "WHERE device_extension_attribute_values.extension_attribute_id = 7 AND "
            "device_extension_attribute_values.device_id = devices.id AND "
            f"{'device_extension_attribute_values.value IS NOT NULL AND ' if operator in ['greaterThan', 'greaterThanOrEqual', 'lessThan', 'lessThanOrEqual'] else ''}"
            f"device_extension_attribute_values.{expected_fragment})"
        ) == sql

    def test_numeric_comparison_adds_null_guard_on_value(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="greaterThan",
                    type=CriteriaType.NUMBER,
                    value="5",
                    extension_attribute_id=7,
                )
            ]
        )
        sql = _compile(result)
        assert (
            "EXISTS (SELECT device_extension_attribute_values.device_id \n"
            "FROM device_extension_attribute_values, devices \n"
            "WHERE device_extension_attribute_values.extension_attribute_id = 7 AND "
            "device_extension_attribute_values.device_id = devices.id AND "
            "device_extension_attribute_values.value IS NOT NULL AND "
            "device_extension_attribute_values.value > '5')"
        ) == sql

    def test_invalid_operator_returns_none(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="bogus",
                    type=CriteriaType.STRING,
                    value="x",
                    extension_attribute_id=7,
                )
            ]
        )
        assert result is None

    def test_ext_attr_criterion_combined_with_device_field(self) -> None:
        result = build_device_query(
            [
                Criteria(
                    field="status",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="ENROLLED",
                    and_or="AND",
                ),
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="x",
                    and_or="AND",
                    extension_attribute_id=7,
                ),
            ]
        )
        sql = _compile(result)
        assert (
            "devices.status = 'ENROLLED' AND (EXISTS (SELECT "
            "device_extension_attribute_values.device_id \n"
            "FROM device_extension_attribute_values, devices \n"
            "WHERE device_extension_attribute_values.extension_attribute_id = 7 AND "
            "device_extension_attribute_values.device_id = devices.id AND "
            "device_extension_attribute_values.value = 'x'))"
        ) == sql


# ---------------------------------------------------------------------------
# Every valid device field
# ---------------------------------------------------------------------------


class TestAllValidFields:
    @pytest.mark.parametrize("field", sorted(VALID_CRITERIA_FIELDS))
    def test_each_valid_field_builds_filter(self, field: str) -> None:
        result = build_device_query([Criteria(field=field, operator="is", type=CriteriaType.STRING, value="v")])
        assert result is not None
        sql = _compile(result)
        assert f"devices.{field}" in sql


# ---------------------------------------------------------------------------
# _partition / _fold_group unit tests
# ---------------------------------------------------------------------------


class TestPartition:
    def test_partitions_by_parentheses(self) -> None:
        groups = _partition(
            [
                Criteria(
                    field="name", operator="is", type=CriteriaType.STRING, value="A", and_or="OR", left_parentheses=True
                ),
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="B",
                    and_or="AND",
                    right_parentheses=True,
                ),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="C"),
            ]
        )
        assert [len(g) for g in groups] == [2, 1]

    def test_single_group_when_no_parentheses(self) -> None:
        groups = _partition(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B"),
            ]
        )
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_empty_criteria_returns_empty_groups(self) -> None:
        assert _partition([]) == []

    def test_skips_invalid_filters(self) -> None:
        groups = _partition(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"),
                Criteria(field="no_such_col", operator="is", type=CriteriaType.STRING, value="B"),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="C"),
            ]
        )
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_consecutive_left_parentheses_start_fresh_groups(self) -> None:
        groups = _partition(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A", left_parentheses=True),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B", left_parentheses=True),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="C"),
            ]
        )
        assert [len(g) for g in groups] == [1, 2]

    def test_unclosed_left_parenthesis_groups_at_end(self) -> None:
        """A leading left paren with no close still forms a single group."""
        groups = _partition(
            [
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A", left_parentheses=True),
                Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B"),
            ]
        )
        assert [len(g) for g in groups] == [2]


class TestFoldGroup:
    def test_single_item_returns_expr_and_trailing_conj(self) -> None:
        expr, trailing = _fold_group(
            [
                (
                    Device.name == "A",
                    "OR",
                )
            ]
        )
        assert trailing == "OR"
        assert "devices.name" in _compile(expr)

    def test_folds_with_each_prior_and_or(self) -> None:
        expr, _ = _fold_group(
            [
                (Device.name == "A", "AND"),
                (Device.name == "B", "OR"),
                (Device.name == "C", "AND"),
            ]
        )
        sql = _compile(expr)
        assert "devices.name = 'A' AND devices.name = 'B' OR devices.name = 'C'" in sql

    def test_trailing_conj_is_last_and_or(self) -> None:
        _, trailing = _fold_group(
            [
                (Device.name == "A", "AND"),
                (Device.name == "B", "OR"),
            ]
        )
        assert trailing == "OR"


# ---------------------------------------------------------------------------
# Group-boundary conjunction semantics
# ---------------------------------------------------------------------------


class TestGroupConjunction:
    def test_parens_emitted_for_precedence(self) -> None:
        """(A OR B) AND C keeps parentheses in the emitted SQL."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="like",
                    type=CriteriaType.STRING,
                    value="A",
                    and_or="OR",
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
                Criteria(field="status", operator="is", type=CriteriaType.STRING, value="ENROLLED"),
            ]
        )
        sql = _compile(result)
        assert "(devices.name LIKE" in sql
        assert "OR devices.name LIKE" in sql
        assert ") AND devices.status = 'ENROLLED'" in sql

    def test_conjunction_between_groups_uses_previous_last_and_or(self) -> None:
        """(A AND B) OR (C AND D): the OR between groups comes from B's and_or.

        SQLAlchemy drops redundant parens when AND binds tighter than OR,
        so the boundary OR shows up between the two AND chains.
        """
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
        assert (
            "devices.name LIKE '%%A%%' AND devices.name LIKE '%%B%%' OR devices.name LIKE '%%C%%' AND devices.name LIKE '%%D%%'"
            in sql
        )

    def test_single_item_group_boundary_conjunction(self) -> None:
        """(A) OR (B): the OR is the trailing conj of the first group."""
        result = build_device_query(
            [
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="A",
                    and_or="OR",
                    left_parentheses=True,
                    right_parentheses=True,
                ),
                Criteria(
                    field="name",
                    operator="is",
                    type=CriteriaType.STRING,
                    value="B",
                    left_parentheses=True,
                    right_parentheses=True,
                ),
            ]
        )
        sql = _compile(result)
        assert "devices.name = 'A' OR devices.name = 'B'" in sql


# ---------------------------------------------------------------------------
# _build_filter unit tests
# ---------------------------------------------------------------------------


class TestBuildFilter:
    def test_valid_field_and_operator(self) -> None:
        c = Criteria(field="name", operator="is", type=CriteriaType.STRING, value="test")
        result = _build_filter(c)
        assert result is not None

    def test_invalid_field_returns_none(self) -> None:
        c = Criteria(field="nonexistent", operator="is", type=CriteriaType.STRING, value="test")
        assert _build_filter(c) is None

    def test_invalid_operator_returns_none(self) -> None:
        c = Criteria(field="name", operator="bogus", type=CriteriaType.STRING, value="test")
        assert _build_filter(c) is None


# ---------------------------------------------------------------------------
# _combine unit tests
# ---------------------------------------------------------------------------


class TestCombine:
    def test_and_combination(self) -> None:
        left = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"))
        right = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B"))
        result = _combine(left, "AND", right)
        sql = _compile(result)
        assert "devices.name = 'A' AND devices.name = 'B'" == sql

    def test_or_combination(self) -> None:
        left = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"))
        right = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B"))
        result = _combine(left, "OR", right)
        sql = _compile(result)
        assert "devices.name = 'A' OR devices.name = 'B'" == sql

    def test_and_is_case_insensitive(self) -> None:
        left = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="A"))
        right = _build_filter(Criteria(field="name", operator="is", type=CriteriaType.STRING, value="B"))
        result_lower = _combine(left, "and", right)
        result_upper = _combine(left, "AND", right)
        assert _compile(result_lower) == _compile(result_upper)
