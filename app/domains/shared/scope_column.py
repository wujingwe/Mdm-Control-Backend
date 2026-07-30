from typing import Any

from sqlalchemy import JSON, Dialect, TypeDecorator

from app.domains.shared.scope import Scope


class ScopeColumnType(TypeDecorator[Scope]):
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Scope | dict[str, Any] | None, dialect: Dialect) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return value.model_dump()

    def process_result_value(self, value: dict[str, Any] | None, dialect: Dialect) -> Scope | None:
        if value is None:
            return None
        return Scope.model_validate(value)
