import pytest
from pydantic import ValidationError

from app.criteria.schemas import Criteria
from app.common.enums import CriteriaType


class TestCriteria:
    def test_valid_string_criteria(self) -> None:
        c = Criteria(
            field="os_version",
            operator="is",
            type=CriteriaType.STRING,
            value="Android 14",
        )
        assert c.field == "os_version"
        assert c.operator == "is"
        assert c.type == CriteriaType.STRING
        assert c.value == "Android 14"
        assert c.left_parentheses is False
        assert c.right_parentheses is False

    def test_valid_number_criteria(self) -> None:
        c = Criteria(
            field="battery_status",
            operator="lessThan",
            type=CriteriaType.NUMBER,
            value="20",
        )
        assert c.type == CriteriaType.NUMBER

    def test_valid_boolean_criteria(self) -> None:
        c = Criteria(
            field="is_managed",
            operator="is",
            type=CriteriaType.BOOLEAN,
            value="true",
        )
        assert c.type == CriteriaType.BOOLEAN

    def test_valid_date_criteria(self) -> None:
        c = Criteria(
            field="last_seen",
            operator="greaterThanOrEqual",
            type=CriteriaType.DATE,
            value="2024-01-01",
        )
        assert c.type == CriteriaType.DATE

    def test_parentheses_default_false(self) -> None:
        c = Criteria(
            field="os_version",
            operator="is",
            type=CriteriaType.STRING,
            value="Android 14",
        )
        assert c.left_parentheses is False
        assert c.right_parentheses is False

    def test_parentheses_explicit_true(self) -> None:
        c = Criteria(
            field="os_version",
            operator="is",
            type=CriteriaType.STRING,
            value="Android 14",
            left_parentheses=True,
            right_parentheses=True,
        )
        assert c.left_parentheses is True
        assert c.right_parentheses is True

    def test_missing_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Criteria(
                operator="is",
                type=CriteriaType.STRING,
                value="test",
            )

    def test_missing_operator_raises(self) -> None:
        with pytest.raises(ValidationError):
            Criteria(
                field="os_version",
                type=CriteriaType.STRING,
                value="test",
            )

    def test_missing_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            Criteria(
                field="os_version",
                operator="is",
                value="test",
            )

    def test_missing_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            Criteria(
                field="os_version",
                operator="is",
                type=CriteriaType.STRING,
            )

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            Criteria(
                field="os_version",
                operator="is",
                type="invalid_type",
                value="test",
            )

    def test_model_dump_roundtrip(self) -> None:
        c = Criteria(
            field="os_version",
            operator="is",
            type=CriteriaType.STRING,
            value="Android 14",
            left_parentheses=True,
        )
        dumped = c.model_dump()
        loaded = Criteria.model_validate(dumped)
        assert loaded.field == c.field
        assert loaded.operator == c.operator
        assert loaded.type == c.type
        assert loaded.value == c.value
        assert loaded.left_parentheses is True

    def test_model_dump_json(self) -> None:
        c = Criteria(
            field="os_version",
            operator="is",
            type=CriteriaType.STRING,
            value="Android 14",
        )
        json_str = c.model_dump_json()
        assert "os_version" in json_str
        assert "is" in json_str
        assert "string" in json_str

    def test_from_dict(self) -> None:
        data = {
            "field": "os_version",
            "operator": "is",
            "type": "string",
            "value": "Android 14",
        }
        c = Criteria.model_validate(data)
        assert c.field == "os_version"
        assert c.type == CriteriaType.STRING

    def test_empty_string_value_allowed(self) -> None:
        c = Criteria(
            field="os_version",
            operator="is",
            type=CriteriaType.STRING,
            value="",
        )
        assert c.value == ""

    def test_empty_string_field_allowed(self) -> None:
        c = Criteria(
            field="",
            operator="is",
            type=CriteriaType.STRING,
            value="test",
        )
        assert c.field == ""


class TestCriteriaTypeEnum:
    def test_string_value(self) -> None:
        assert CriteriaType.STRING == "string"

    def test_number_value(self) -> None:
        assert CriteriaType.NUMBER == "number"

    def test_boolean_value(self) -> None:
        assert CriteriaType.BOOLEAN == "boolean"

    def test_date_value(self) -> None:
        assert CriteriaType.DATE == "date"

    def test_all_values(self) -> None:
        values = {e.value for e in CriteriaType}
        assert values == {"string", "number", "boolean", "date"}
