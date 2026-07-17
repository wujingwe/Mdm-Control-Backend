from enum import Enum


class CriteriaType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"


class SearchOperator(str, Enum):
    IS = "is"
    IS_NOT = "isNot"
    LIKE = "like"
    NOT_LIKE = "notLike"
    MATCHES_REGEX = "matchesRegex"
    DOES_NOT_MATCH_REGEX = "doesNotMatchRegex"
    GREATER_THAN = "greaterThen"
    GREATER_THAN_OR_EQUAL = "greaterThanOrEqual"
    LESS_THAN = "lessThan"
    LESS_THAN_OR_EQUAL = "lessThanOrEqual"


class Conjunction(str, Enum):
    AND = "and"
    OR = "or"


class Criteria:
    open_paren: str
    field: str
    type: CriteriaType
    operator: SearchOperator
    value: str
    close_paren: str
    conjunction: Conjunction
