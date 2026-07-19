from app.common.enums import AssignmentSource, AssignmentStatus
from app.common.schemas import Scope, ScopeType
from app.profiles.schemas import AssignmentUpsert

SCOPE_TO_SOURCE: dict[ScopeType, AssignmentSource] = {
    ScopeType.ALL_DEVICES: AssignmentSource.ALL_DEVICES,
    ScopeType.SMART_GROUP: AssignmentSource.SMART_GROUP,
    ScopeType.STATIC_GROUP: AssignmentSource.STATIC_GROUP,
    ScopeType.DEVICE: AssignmentSource.DIRECT,
}


class AssignmentCalculator:
    @staticmethod
    def compute(
        profile_id: int,
        profile_version: int,
        scope: Scope,
        resolved_device_ids: dict[tuple[str, int], set[int | str]],
    ) -> list[AssignmentUpsert]:
        wanted: dict[tuple[str, int], set[int | str]] = {}
        for target in scope.targets:
            target_id = target.target_id or 0
            source_key = (target.scope_type.value, target_id)
            wanted.setdefault(source_key, set()).update(
                resolved_device_ids.get(source_key, set())
            )

        assignments: list[AssignmentUpsert] = []
        seen: set[int | str] = set()

        for (source_type, source_id), device_ids in wanted.items():
            scope_type = ScopeType(source_type)
            source = SCOPE_TO_SOURCE[scope_type]
            for device_id in device_ids:
                if device_id in seen:
                    continue
                seen.add(device_id)
                assignments.append(
                    AssignmentUpsert(
                        profile_id=profile_id,
                        device_id=int(device_id) if isinstance(device_id, int) else 0,
                        source=source,
                        source_id=source_id if source_id else None,
                        status=AssignmentStatus.PENDING,
                        profile_version=profile_version,
                    )
                )

        if scope.exclusions:
            excluded_ids: set[int | str] = set()
            for exclusion in scope.exclusions:
                excl_id = exclusion.exclude_id or 0
                key = (exclusion.scope_type.value, excl_id)
                excluded_ids.update(resolved_device_ids.get(key, set()))
            assignments = [
                a
                for a in assignments
                if (a.device_id if isinstance(a.device_id, int) else 0)
                not in excluded_ids
            ]

        return assignments
