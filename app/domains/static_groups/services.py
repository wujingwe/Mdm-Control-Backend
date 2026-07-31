from app.domains.shared.group_service import GroupScopeService
from app.domains.shared.scope import ScopeType
from app.domains.static_groups.models import StaticGroup


class StaticGroupService(GroupScopeService[StaticGroup]):
    scope_type = ScopeType.STATIC_GROUP
    entity_label = "static group"
