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


def scope_entry_matches(entry: ScopeTarget | ScopeExclusion, scope_type: ScopeType, target_id: int) -> bool:
    """Whether a single scope entry matches the given entity.

    ALL_DEVICES references every device, so its id is never compared.
    """
    if entry.scope_type != scope_type:
        return False
    if scope_type == ScopeType.ALL_DEVICES:
        return True
    entry_id = entry.target_id if isinstance(entry, ScopeTarget) else entry.exclude_id
    return (entry_id or 0) == target_id


def scope_matches(scope: Scope, scope_type: ScopeType, target_id: int) -> bool:
    """Whether the scope references the given entity as a target or exclusion."""
    return any(scope_entry_matches(target, scope_type, target_id) for target in scope.targets) or any(
        scope_entry_matches(exclusion, scope_type, target_id) for exclusion in scope.exclusions
    )
