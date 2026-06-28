from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.engine.interfaces import Dialect

from app.schemas.device import CertificateInfo, NetworkInfo

S = TypeVar("S")
T = TypeVar("T")


class JsonType(TypeDecorator[T], ABC, Generic[S, T]):
    impl = JSON

    def process_bind_param(self, value: T | None, dialect: Dialect) -> S | None:
        if value is None:
            return None
        return self._bind(value)

    def process_result_value(self, value: S | None, dialect: Dialect) -> T | None:
        if value is None:
            return None
        return self._result(value)

    @abstractmethod
    def _bind(self, value: T) -> S: ...

    @abstractmethod
    def _result(self, value: S) -> T: ...


class NetworkInfoType(JsonType[dict, NetworkInfo]):
    def _bind(self, value: NetworkInfo) -> dict:
        return value.model_dump()

    def _result(self, value: dict) -> NetworkInfo:
        return NetworkInfo.model_validate(value)


class CertificateListType(JsonType[list[dict], list[CertificateInfo]]):
    def _bind(self, value: list[CertificateInfo]) -> list[dict]:
        return [c.model_dump() for c in value]

    def _result(self, value: list[dict]) -> list[CertificateInfo]:
        return [CertificateInfo.model_validate(c) for c in value]


class PermissionListType(JsonType[list[str], frozenset[str]]):
    VALID_PERMISSIONS = frozenset({"admin", "editor", "viewer"})

    def _bind(self, value: frozenset[str]) -> list[str]:
        items = sorted(value)
        for p in items:
            if p not in self.VALID_PERMISSIONS:
                raise ValueError(f"Invalid permission: {p!r}; must be one of {sorted(self.VALID_PERMISSIONS)}")
        return items

    def _result(self, value: list[str]) -> frozenset[str]:
        return frozenset(value)
