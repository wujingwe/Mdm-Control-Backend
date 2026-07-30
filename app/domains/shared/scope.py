from enum import Enum

from app.infra.common.schemas import CamelModel


class ScopeType(str, Enum):
    ALL_DEVICES = "ALL_DEVICES"
    SMART_GROUP = "SMART_GROUP"
    STATIC_GROUP = "STATIC_GROUP"
    DEVICE = "DEVICE"


class ScopeTarget(CamelModel):
    scope_type: ScopeType
    target_id: int | None = None


class ScopeExclusion(CamelModel):
    scope_type: ScopeType
    exclude_id: int | None = None


class Scope(CamelModel):
    targets: list[ScopeTarget] = []
    exclusions: list[ScopeExclusion] = []
    
