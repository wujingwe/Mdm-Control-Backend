from app.domains.shared.group_service import GroupScopeService
from app.domains.shared.scope import ScopeType
from app.domains.static_groups.models import StaticGroup
from app.domains.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate


class StaticGroupService(GroupScopeService[StaticGroup, StaticGroupCreate, StaticGroupUpdate]):
    scope_type = ScopeType.STATIC_GROUP
    entity_label = "static group"
