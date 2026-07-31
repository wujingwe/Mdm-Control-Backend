from app.domains.shared.group_service import GroupScopeService
from app.domains.shared.scope import ScopeType
from app.domains.smart_groups.models import SmartGroup


class SmartGroupService(GroupScopeService[SmartGroup]):
    scope_type = ScopeType.SMART_GROUP
    entity_label = "smart group"
