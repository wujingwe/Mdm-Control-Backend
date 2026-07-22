from app.common.schemas import Scope, Target, Exclusion, ScopeType
from app.profiles.reconciler import ProfileAssignmentReconciler


class TestAssignmentCalculator:
    def test_empty_scope(self) -> None:
        scope = Scope()
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids={}
        )
        assert result == []

    def test_all_devices_target(self) -> None:
        scope = Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)])
        resolved = {(ScopeType.ALL_DEVICES.value, 0): {1, 2, 3}}
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 3
        device_ids = {a.device_id for a in result}
        assert device_ids == {1, 2, 3}

    def test_smart_group_target(self) -> None:
        scope = Scope(targets=[Target(scope_type=ScopeType.SMART_GROUP, target_id=5)])
        resolved = {(ScopeType.SMART_GROUP.value, 5): {10, 20}}
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 2
        assert result[0].profile_version == 1

    def test_static_group_target(self) -> None:
        scope = Scope(targets=[Target(scope_type=ScopeType.STATIC_GROUP, target_id=3)])
        resolved = {(ScopeType.STATIC_GROUP.value, 3): {101, 102}}
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 2

    def test_device_target(self) -> None:
        scope = Scope(targets=[Target(scope_type=ScopeType.DEVICE, target_id=42)])
        resolved = {(ScopeType.DEVICE.value, 42): {42}}
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 1
        assert result[0].device_id == 42

    def test_multiple_targets(self) -> None:
        scope = Scope(
            targets=[
                Target(scope_type=ScopeType.SMART_GROUP, target_id=1),
                Target(scope_type=ScopeType.STATIC_GROUP, target_id=2),
            ]
        )
        resolved = {
            (ScopeType.SMART_GROUP.value, 1): {10, 20},
            (ScopeType.STATIC_GROUP.value, 2): {20, 30},
        }
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {10, 20, 30}

    def test_exclusion_filters_devices(self) -> None:
        scope = Scope(
            targets=[Target(scope_type=ScopeType.ALL_DEVICES)],
            exclusions=[Exclusion(scope_type=ScopeType.DEVICE, exclude_id=2)],
        )
        resolved = {
            (ScopeType.ALL_DEVICES.value, 0): {1, 2, 3},
            (ScopeType.DEVICE.value, 2): {2},
        }
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {1, 3}

    def test_exclusion_from_resolved_not_in_targets(self) -> None:
        scope = Scope(
            targets=[Target(scope_type=ScopeType.SMART_GROUP, target_id=1)],
            exclusions=[Exclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=2)],
        )
        resolved = {
            (ScopeType.SMART_GROUP.value, 1): {10, 20, 30},
            (ScopeType.SMART_GROUP.value, 2): {20, 30},
        }
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {10}

    def test_no_resolved_ids_for_target(self) -> None:
        scope = Scope(targets=[Target(scope_type=ScopeType.SMART_GROUP, target_id=99)])
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids={}
        )
        assert result == []

    def test_assignment_fields(self) -> None:
        scope = Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)])
        resolved = {(ScopeType.ALL_DEVICES.value, 0): {1}}
        result = ProfileAssignmentReconciler.compute(
            profile_id=7, profile_version=3, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 1
        a = result[0]
        assert a.profile_id == 7
        assert a.profile_version == 3
        assert a.status.value == "PENDING"

    def test_deduplication_across_targets(self) -> None:
        scope = Scope(
            targets=[
                Target(scope_type=ScopeType.SMART_GROUP, target_id=1),
                Target(scope_type=ScopeType.SMART_GROUP, target_id=2),
            ]
        )
        resolved = {
            (ScopeType.SMART_GROUP.value, 1): {10, 20},
            (ScopeType.SMART_GROUP.value, 2): {20, 30},
        }
        result = ProfileAssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {10, 20, 30}
        assert len(result) == 3
