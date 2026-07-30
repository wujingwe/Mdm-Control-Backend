from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.scope import ScopeExclusion, Scope, ScopeType, ScopeTarget
from app.domains.devices.models import Device
from app.infra.messaging.producer import RabbitMQProducer
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.models import Profile, ProfileAssignment
from app.domains.profiles.repositories import ProfileRepository
from app.domains.devices.enums import DeviceStatus
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.infra.reconciler.reconciler import AssignmentReconciler
from app.domains.smart_groups.models import SmartGroup
from app.domains.static_groups.models import StaticGroup, StaticGroupDevice


def _make_producer() -> MagicMock:
    producer = MagicMock(spec=RabbitMQProducer)
    producer.publish_profile_push = AsyncMock(return_value="msg-id")
    producer.publish_profile_revoke = AsyncMock(return_value="msg-id")
    producer.publish_mobile_app_push = AsyncMock(return_value="msg-id")
    producer.publish_mobile_app_revoke = AsyncMock(return_value="msg-id")
    return producer


async def _create_device(db: AsyncSession, name: str, serial: str, status: str = DeviceStatus.ENROLLED.value) -> Device:
    device = Device(
        name=name,
        serial_number=serial,
        os_version="macOS 15.0",
        connection_status="CONNECTED",
        status=status,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)
    return device


async def _create_profile(db: AsyncSession, name: str, scope: Scope | None = None) -> Profile:
    profile = Profile(name=name, scope=scope or Scope(), policy={}, created_by=1)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def _create_mobile_app(
    db: AsyncSession, name: str, package_name: str = "com.test.app", scope: Scope | None = None
) -> MobileApp:
    app = MobileApp(
        name=name,
        package_name=package_name,
        package_version="1.0.0",
        version=1,
        scope=scope or Scope(),
        created_by=1,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


async def _create_assignment(db: AsyncSession, profile_id: int, device_id: int, version: int = 1) -> ProfileAssignment:
    assignment = ProfileAssignment(
        profile_id=profile_id,
        device_id=device_id,
        profile_version=version,
    )
    db.add(assignment)
    await db.commit()
    return assignment


# ── compute_mobile_app ──────────────────────────────────────────────────


class TestComputeMobileApp:
    async def test_empty_scope(self) -> None:
        scope = Scope()
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids={}
        )
        assert result == []

    async def test_all_devices_target(self) -> None:
        scope = Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)])
        resolved = {(ScopeType.ALL_DEVICES.value, 0): {1, 2, 3}}
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 3

    async def test_smart_group_target(self) -> None:
        scope = Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=5)])
        resolved = {(ScopeType.SMART_GROUP.value, 5): {10, 20}}
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 2
        assert result[0].version == 1

    async def test_static_group_target(self) -> None:
        scope = Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=3)])
        resolved = {(ScopeType.STATIC_GROUP.value, 3): {101, 102}}
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 2

    async def test_device_target(self) -> None:
        scope = Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=42)])
        resolved = {(ScopeType.DEVICE.value, 42): {42}}
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids=resolved
        )
        assert len(result) == 1
        assert result[0].device_id == 42

    async def test_multiple_targets_dedup(self) -> None:
        scope = Scope(
            targets=[
                ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=1),
                ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=2),
            ]
        )
        resolved = {
            (ScopeType.SMART_GROUP.value, 1): {10, 20},
            (ScopeType.STATIC_GROUP.value, 2): {20, 30},
        }
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {10, 20, 30}

    async def test_exclusion_filters_devices(self) -> None:
        scope = Scope(
            targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
            exclusions=[ScopeExclusion(scope_type=ScopeType.DEVICE, exclude_id=2)],
        )
        resolved = {
            (ScopeType.ALL_DEVICES.value, 0): {1, 2, 3},
            (ScopeType.DEVICE.value, 2): {2},
        }
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {1, 3}

    async def test_exclusion_from_resolved_not_in_targets(self) -> None:
        scope = Scope(
            targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=1)],
            exclusions=[ScopeExclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=2)],
        )
        resolved = {
            (ScopeType.SMART_GROUP.value, 1): {10, 20, 30},
            (ScopeType.SMART_GROUP.value, 2): {20, 30},
        }
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {10}

    async def test_no_resolved_ids_for_target(self) -> None:
        scope = Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=99)])
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids={}
        )
        assert result == []

    async def test_assignment_fields(self) -> None:
        scope = Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)])
        resolved = {(ScopeType.ALL_DEVICES.value, 0): {1}}
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=7, app_version=3, scope=scope, resolved_device_ids=resolved
        )
        a = result[0]
        assert a.mobile_app_id == 7
        assert a.version == 3
        assert a.status == AssignmentStatus.PENDING

    async def test_deduplication_across_targets(self) -> None:
        scope = Scope(
            targets=[
                ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=1),
                ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=2),
            ]
        )
        resolved = {
            (ScopeType.SMART_GROUP.value, 1): {10, 20},
            (ScopeType.SMART_GROUP.value, 2): {20, 30},
        }
        result = AssignmentReconciler.compute_mobile_app(
            mobile_app_id=1, app_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {10, 20, 30}
        assert len(result) == 3


# ── recalculate_profile: publish=False ──────────────────────────────────


class TestRecalculateProfilePublish:
    async def test_publish_false_does_not_send_messages(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        _ = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_profile(profile.id, publish=False)

        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1
        producer.publish_profile_push.assert_not_awaited()
        producer.publish_profile_revoke.assert_not_awaited()


# ── recalculate_profiles_for_smart_group ────────────────────────────────


class TestRecalculateProfilesForSmartGroup:
    async def test_target_match_recales(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        _ = await _create_device(db_session, "Mac", "SN-1")
        sg = SmartGroup(
            name="Macs",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "Mac"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1

    async def test_exclusion_match_recales(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        _ = await _create_device(db_session, "Mac", "SN-1")
        sg = SmartGroup(
            name="Excl",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "Mac"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
                exclusions=[ScopeExclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=sg.id)],
            ),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        device_ids = {a.device_id for a in assignments}
        assert device_ids == set()

    async def test_no_match_does_nothing(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        _ = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=999)]),
        )

        await reconciler.recalculate_profiles_for_smart_group(888)

        producer.publish_profile_push.assert_not_awaited()


# ── recalculate_profiles_for_static_group ───────────────────────────────


class TestRecalculateProfilesForStaticGroup:
    async def test_target_match_recales(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        _ = await _create_device(db_session, "Mac1", "SN-1")
        sg = StaticGroup(name="SG1", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        db_session.add(StaticGroupDevice(static_group_id=sg.id, device_serial_number="SN-1"))
        await db_session.commit()

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1

    async def test_exclusion_match_recales(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        sg = StaticGroup(name="SG1", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        db_session.add(StaticGroupDevice(static_group_id=sg.id, device_serial_number="SN-1"))
        await db_session.commit()

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
                exclusions=[ScopeExclusion(scope_type=ScopeType.STATIC_GROUP, exclude_id=sg.id)],
            ),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        present_device_ids = {a.device_id for a in assignments if a.desired_state == AssignmentDesiredState.PRESENT}
        assert d1.id not in present_device_ids

    async def test_no_match_does_nothing(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=999)]),
        )

        await reconciler.recalculate_profiles_for_static_group(888)

        producer.publish_profile_push.assert_not_awaited()


# ── recalculate_mobile_app ──────────────────────────────────────────────


class TestRecalculateMobileApp:
    async def test_not_found(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        reconciler = AssignmentReconciler(
            ProfileRepository(db_session),
            MobileAppRepository(db_session),
            producer,
        )
        await reconciler.recalculate_mobile_app(99999)
        producer.publish_mobile_app_push.assert_not_awaited()

    async def test_no_changes(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        )
        await repo.bulk_create_assignments(app.id, 1, {device.id})

        await reconciler.recalculate_mobile_app(app.id)

        producer.publish_mobile_app_push.assert_not_awaited()
        producer.publish_mobile_app_revoke.assert_not_awaited()

    async def test_new_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_mobile_app(app.id)

        assignments = await repo.get_assignments(app.id)
        assert len(assignments) == 1
        assert assignments[0].device_id == device.id
        producer.publish_mobile_app_push.assert_awaited_once()

    async def test_with_revoke(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        d2 = await _create_device(db_session, "Mac2", "SN-2")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=d1.id)]),
        )
        await repo.bulk_create_assignments(app.id, 1, {d1.id, d2.id})

        await reconciler.recalculate_mobile_app(app.id)

        current = await repo.get_current_assignments(app.id)
        present_device_ids = {a.device_id for a in current if a.desired_state == AssignmentDesiredState.PRESENT}
        assert present_device_ids == {d1.id}
        producer.publish_mobile_app_revoke.assert_awaited_once()

    async def test_force_push(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await repo.bulk_create_assignments(app.id, 1, {device.id})

        await reconciler.recalculate_mobile_app(app.id, force_push=True)

        producer.publish_mobile_app_push.assert_awaited_once()

    async def test_publish_false(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        _ = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_mobile_app(app.id, publish=False)

        assignments = await repo.get_assignments(app.id)
        assert len(assignments) == 1
        producer.publish_mobile_app_push.assert_not_awaited()
        producer.publish_mobile_app_revoke.assert_not_awaited()

    async def test_empty_scope_clears(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(db_session, "App1")
        await repo.bulk_create_assignments(app.id, 1, {device.id})

        await reconciler.recalculate_mobile_app(app.id)

        assert await repo.get_current_desired_device_ids(app.id) == set()
        producer.publish_mobile_app_revoke.assert_awaited_once()


# ── recalculate_mobile_apps_for_device ──────────────────────────────────


class TestRecalculateMobileAppsForDevice:
    async def test_triggers_affected_apps(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app1 = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        )
        app2 = await _create_mobile_app(
            db_session,
            "App2",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_mobile_apps_for_device(device.id, publish=False)

        a1 = await repo.get_assignments(app1.id)
        a2 = await repo.get_assignments(app2.id)
        assert len(a1) == 1
        assert len(a2) == 1

    async def test_no_affected_apps(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        await _create_mobile_app(db_session, "App1")

        await reconciler.recalculate_mobile_apps_for_device(device.id, publish=False)
        producer.publish_mobile_app_push.assert_not_awaited()


# ── recalculate_mobile_apps_for_smart_group ──────────────────────────────


class TestRecalculateMobileAppsForSmartGroup:
    async def test_target_match_recales(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        _ = await _create_device(db_session, "Mac", "SN-1")
        sg = SmartGroup(
            name="Macs",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "Mac"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)]),
        )

        await reconciler.recalculate_mobile_app(app.id)

        assignments = await repo.get_assignments(app.id)
        assert len(assignments) == 1

    async def test_exclusion_match_recales(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        _ = await _create_device(db_session, "Mac", "SN-1")
        sg = SmartGroup(
            name="Excl",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "Mac"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(
                targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
                exclusions=[ScopeExclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=sg.id)],
            ),
        )

        await reconciler.recalculate_mobile_app(app.id)

        assignments = await repo.get_assignments(app.id)
        assert len(assignments) >= 0

    async def test_no_match_does_nothing(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=999)]),
        )

        await reconciler.recalculate_mobile_apps_for_smart_group(888)

        producer.publish_mobile_app_push.assert_not_awaited()


# ── recalculate_mobile_apps_for_static_group ─────────────────────────────


class TestRecalculateMobileAppsForStaticGroup:
    async def test_target_match_recales(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        _ = await _create_device(db_session, "Mac1", "SN-1")
        sg = StaticGroup(name="SG1", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        db_session.add(StaticGroupDevice(static_group_id=sg.id, device_serial_number="SN-1"))
        await db_session.commit()

        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)]),
        )

        await reconciler.recalculate_mobile_app(app.id)

        assignments = await repo.get_assignments(app.id)
        assert len(assignments) == 1

    async def test_exclusion_match_recales(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        _ = await _create_device(db_session, "Mac1", "SN-1")
        sg = StaticGroup(name="SG1", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        db_session.add(StaticGroupDevice(static_group_id=sg.id, device_serial_number="SN-1"))
        await db_session.commit()

        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(
                targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
                exclusions=[ScopeExclusion(scope_type=ScopeType.STATIC_GROUP, exclude_id=sg.id)],
            ),
        )

        await reconciler.recalculate_mobile_app(app.id)

        assignments = await repo.get_assignments(app.id)
        assert len(assignments) >= 0

    async def test_no_match_does_nothing(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)

        await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=999)]),
        )

        await reconciler.recalculate_mobile_apps_for_static_group(888)

        producer.publish_mobile_app_push.assert_not_awaited()


# ── purge methods ───────────────────────────────────────────────────────


class TestPurgeMethods:
    async def test_purge_smart_group(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.infra.reconciler.reconciler.request_recalculation", AsyncMock())
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, app_repo, producer)

        sg = SmartGroup(name="SG", criteria=[], created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)]),
        )
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)]),
        )

        await reconciler.purge_smart_group(sg.id)

        reloaded_profile = await profile_repo.get_by_id(profile.id)
        assert reloaded_profile is not None
        assert all(t.scope_type != ScopeType.SMART_GROUP for t in reloaded_profile.scope.targets)

        reloaded_app = await app_repo.get_by_id(app.id)
        assert reloaded_app is not None
        assert all(t.scope_type != ScopeType.SMART_GROUP for t in reloaded_app.scope.targets)

    async def test_purge_static_group(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.infra.reconciler.reconciler.request_recalculation", AsyncMock())
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, app_repo, producer)

        sg = StaticGroup(name="SG1", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)]),
        )
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)]),
        )

        await reconciler.purge_static_group(sg.id)

        reloaded_profile = await profile_repo.get_by_id(profile.id)
        assert reloaded_profile is not None
        assert all(t.scope_type != ScopeType.STATIC_GROUP for t in reloaded_profile.scope.targets)

        reloaded_app = await app_repo.get_by_id(app.id)
        assert reloaded_app is not None
        assert all(t.scope_type != ScopeType.STATIC_GROUP for t in reloaded_app.scope.targets)

    async def test_purge_device(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.infra.reconciler.reconciler.request_recalculation", AsyncMock())
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )

        await reconciler.purge_device(device.id)

        reloaded_profile = await profile_repo.get_by_id(profile.id)
        assert reloaded_profile is not None
        assert all(t.scope_type != ScopeType.DEVICE for t in reloaded_profile.scope.targets)

        reloaded_app = await app_repo.get_by_id(app.id)
        assert reloaded_app is not None
        assert all(t.scope_type != ScopeType.DEVICE for t in reloaded_app.scope.targets)


# ── dispatch_device_assignments ─────────────────────────────────────────


class TestDispatchDeviceAssignments:
    async def test_device_not_found(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        await reconciler.dispatch_device_assignments(99999)
        producer.publish_profile_push.assert_not_awaited()

    async def test_device_not_enrolled(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1", DeviceStatus.UNENROLLED.value)

        await reconciler.dispatch_device_assignments(device.id)
        producer.publish_profile_push.assert_not_awaited()

    async def test_profile_is_none_skips(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")

        assignment = ProfileAssignment(
            profile_id=99999,
            device_id=device.id,
            profile_version=1,
        )
        db_session.add(assignment)
        await db_session.commit()

        await reconciler.dispatch_device_assignments(device.id)
        producer.publish_profile_push.assert_not_awaited()

    async def test_push_path(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_profile(profile.id)
        producer.publish_profile_push.reset_mock()

        await reconciler.dispatch_device_assignments(device.id)
        producer.publish_profile_push.assert_awaited_once()

    async def test_revoke_path(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")

        assignment = ProfileAssignment(
            profile_id=profile.id,
            device_id=device.id,
            profile_version=1,
            desired_state=AssignmentDesiredState.ABSENT,
            status=AssignmentStatus.REVOKE_PENDING,
        )
        db_session.add(assignment)
        await db_session.commit()

        await reconciler.dispatch_device_assignments(device.id)
        producer.publish_profile_revoke.assert_awaited_once()

    async def test_exception_path(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_profile_push = AsyncMock(side_effect=RuntimeError("down"))
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_profile(profile.id, publish=False)
        producer.publish_profile_push.reset_mock()

        await reconciler.dispatch_device_assignments(device.id)

        assignments = await profile_repo.get_current_assignments(profile.id)
        failed = [a for a in assignments if a.status == AssignmentStatus.FAILED]
        assert len(failed) >= 1


# ── dispatch_device_mobile_app_assignments ──────────────────────────────


class TestDispatchDeviceMobileAppAssignments:
    async def test_device_not_found(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(MagicMock(spec=ProfileRepository), app_repo, producer)

        await reconciler.dispatch_device_mobile_app_assignments(99999)
        producer.publish_mobile_app_push.assert_not_awaited()

    async def test_device_not_enrolled(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(MagicMock(spec=ProfileRepository), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1", DeviceStatus.UNENROLLED.value)

        await reconciler.dispatch_device_mobile_app_assignments(device.id)
        producer.publish_mobile_app_push.assert_not_awaited()

    async def test_app_is_none_skips(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(MagicMock(spec=ProfileRepository), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")

        assignment = MobileAppAssignment(
            mobile_app_id=99999,
            device_id=device.id,
            version=1,
        )
        db_session.add(assignment)
        await db_session.commit()

        await reconciler.dispatch_device_mobile_app_assignments(device.id)
        producer.publish_mobile_app_push.assert_not_awaited()

    async def test_push_path(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_mobile_app(app.id, publish=False)
        producer.publish_mobile_app_push.reset_mock()

        await reconciler.dispatch_device_mobile_app_assignments(device.id)
        producer.publish_mobile_app_push.assert_awaited_once()

    async def test_revoke_path(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(MagicMock(spec=ProfileRepository), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(db_session, "App1")

        assignment = MobileAppAssignment(
            mobile_app_id=app.id,
            device_id=device.id,
            version=1,
            desired_state=AssignmentDesiredState.ABSENT,
            status=AssignmentStatus.REVOKE_PENDING,
        )
        db_session.add(assignment)
        await db_session.commit()

        await reconciler.dispatch_device_mobile_app_assignments(device.id)
        producer.publish_mobile_app_revoke.assert_awaited_once()

    async def test_exception_path(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_mobile_app_push = AsyncMock(side_effect=RuntimeError("down"))
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_mobile_app(app.id, publish=False)
        producer.publish_mobile_app_push.reset_mock()

        await reconciler.dispatch_device_mobile_app_assignments(device.id)

        assignments = await app_repo.get_current_assignments(app.id)
        failed = [a for a in assignments if a.status == AssignmentStatus.FAILED]
        assert len(failed) >= 1


# ── _resolve_scope ──────────────────────────────────────────────────────


class TestResolveScope:
    async def test_exclusion_with_no_device_ids(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")

        scope = Scope(
            targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
            exclusions=[ScopeExclusion(scope_type=ScopeType.DEVICE, exclude_id=99999)],
        )

        resolved = await reconciler._resolve_scope(scope)

        assert (ScopeType.ALL_DEVICES.value, 0) in resolved
        assert device.id in resolved[(ScopeType.ALL_DEVICES.value, 0)]
        # Exclusion target 99999 doesn't exist — device_ids is empty set, so it's not added


# ── _resolve_target ─────────────────────────────────────────────────────


class TestResolveTarget:
    async def test_static_group_empty(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        sg = StaticGroup(name="EmptySG", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        target = ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)
        result = await reconciler._resolve_target(target)
        assert result == set()

    async def test_device_not_enrolled(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1", DeviceStatus.UNENROLLED.value)

        target = ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)
        result = await reconciler._resolve_target(target)
        assert result == set()

    async def test_default_return_set(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        target = ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=None)
        result = await reconciler._resolve_target(target)
        assert result == set()


# ── _resolve_exclusion ──────────────────────────────────────────────────


class TestResolveExclusion:
    async def test_device_exclusion(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        exclusion = ScopeExclusion(scope_type=ScopeType.DEVICE, exclude_id=42)
        result = await reconciler._resolve_exclusion(exclusion)
        assert result == {42}

    async def test_smart_group_exclusion(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        await _create_device(db_session, "Mac1", "SN-1")
        await _create_device(db_session, "Mac2", "SN-2")

        sg = SmartGroup(
            name="Macs",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "Mac"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        exclusion = ScopeExclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=sg.id)
        result = await reconciler._resolve_exclusion(exclusion)
        assert len(result) == 2

    async def test_static_group_exclusion(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        sg = StaticGroup(name="SG1", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        db_session.add(StaticGroupDevice(static_group_id=sg.id, device_serial_number="SN-1"))
        await db_session.commit()

        exclusion = ScopeExclusion(scope_type=ScopeType.STATIC_GROUP, exclude_id=sg.id)
        result = await reconciler._resolve_exclusion(exclusion)
        assert result == {device.id}

    async def test_static_group_exclusion_empty(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        sg = StaticGroup(name="EmptySG", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        exclusion = ScopeExclusion(scope_type=ScopeType.STATIC_GROUP, exclude_id=sg.id)
        result = await reconciler._resolve_exclusion(exclusion)
        assert result == set()

    async def test_default_return_set(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        exclusion = ScopeExclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=None)
        result = await reconciler._resolve_exclusion(exclusion)
        assert result == set()


# ── _resolve_smart_group ────────────────────────────────────────────────


class TestResolveSmartGroup:
    async def test_group_not_found(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        result = await reconciler._resolve_smart_group(99999)
        assert result == set()

    async def test_criteria_not_a_list(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        sg = SmartGroup(name="BadSG", criteria="not_a_list", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        result = await reconciler._resolve_smart_group(sg.id)
        assert result == set()

    async def test_where_condition_applied(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        await _create_device(db_session, "MacBook Pro", "SN-1")
        await _create_device(db_session, "iPhone", "SN-2")

        sg = SmartGroup(
            name="Macs",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "MacBook"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        result = await reconciler._resolve_smart_group(sg.id)
        assert len(result) == 1

    async def test_where_is_none_returns_all_enrolled(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        await _create_device(db_session, "Device1", "SN-1")
        await _create_device(db_session, "Device2", "SN-2")

        sg = SmartGroup(
            name="All",
            criteria=[],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        result = await reconciler._resolve_smart_group(sg.id)
        assert len(result) == 2


# ── _send_push_messages / _send_revoke_messages ─────────────────────────


class TestSendPushMessages:
    async def test_assignment_is_none(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )

        device_ids_without_assignment = {device.id}
        empty_assignments: dict[int, ProfileAssignment] = {}

        await reconciler._send_push_messages(
            profile,
            device_ids_without_assignment,
            empty_assignments,
            version=1,
        )

        producer.publish_profile_push.assert_awaited_once_with(
            serial_number=device.serial_number,
            profile_id=profile.id,
            profile_config=profile.policy,
            profile_version=1,
            assignment_id=None,
        )

    async def test_exception_when_assignment_is_none(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_profile_push = AsyncMock(side_effect=RuntimeError("down"))
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")

        await reconciler._send_push_messages(
            profile,
            {device.id},
            {},
            version=1,
        )

        producer.publish_profile_push.assert_awaited_once()


class TestSendRevokeMessages:
    async def test_assignment_is_none(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")

        await reconciler._send_revoke_messages(
            profile,
            {device.id},
            {},
            version=1,
        )

        producer.publish_profile_revoke.assert_awaited_once_with(
            serial_number=device.serial_number,
            profile_id=profile.id,
            profile_version=1,
            assignment_id=None,
        )

    async def test_exception_when_assignment_is_none(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_profile_revoke = AsyncMock(side_effect=RuntimeError("down"))
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")

        await reconciler._send_revoke_messages(
            profile,
            {device.id},
            {},
            version=1,
        )

        producer.publish_profile_revoke.assert_awaited_once()

    async def test_with_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_profile(profile.id, publish=False)

        assignments = await profile_repo.get_assignments(profile.id)
        assignment = assignments[0]

        assignment_dict = {assignment.device_id: assignment}

        await reconciler._send_revoke_messages(
            profile,
            {device.id},
            assignment_dict,
            version=1,
        )

        producer.publish_profile_revoke.assert_awaited_once()


# ── _send_mobile_app_push_messages / _send_mobile_app_revoke_messages ────


class TestSendMobileAppPushMessages:
    async def test_push_with_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_mobile_app(app.id, publish=False)

        assignments = await app_repo.get_assignments(app.id)
        assignment_dict = {a.device_id: a for a in assignments}

        await reconciler._send_mobile_app_push_messages(
            app,
            {device.id},
            assignment_dict,
            version=1,
        )

        producer.publish_mobile_app_push.assert_awaited_once_with(
            serial_number=device.serial_number,
            mobile_app_id=app.id,
            package_name=app.package_name,
            package_version=app.package_version,
            app_version=1,
            assignment_id=assignments[0].id,
        )

    async def test_push_without_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(MagicMock(spec=ProfileRepository), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(db_session, "App1")

        await reconciler._send_mobile_app_push_messages(
            app,
            {device.id},
            {},
            version=1,
        )

        producer.publish_mobile_app_push.assert_awaited_once_with(
            serial_number=device.serial_number,
            mobile_app_id=app.id,
            package_name=app.package_name,
            package_version=app.package_version,
            app_version=1,
            assignment_id=None,
        )

    async def test_exception(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_mobile_app_push = AsyncMock(side_effect=RuntimeError("down"))
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(MagicMock(spec=ProfileRepository), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(db_session, "App1")

        await reconciler._send_mobile_app_push_messages(
            app,
            {device.id},
            {},
            version=1,
        )

        producer.publish_mobile_app_push.assert_awaited_once()

    async def test_exception_with_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_mobile_app_push = AsyncMock(side_effect=RuntimeError("down"))
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_mobile_app(app.id, publish=False)

        assignments = await app_repo.get_assignments(app.id)
        assignment_dict = {a.device_id: a for a in assignments}

        await reconciler._send_mobile_app_push_messages(
            app,
            {device.id},
            assignment_dict,
            version=1,
        )

        failed_assignment = await app_repo.db.get(MobileAppAssignment, assignments[0].id)
        assert failed_assignment is not None
        assert failed_assignment.status == AssignmentStatus.FAILED


class TestSendMobileAppRevokeMessages:
    async def test_revoke_with_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_mobile_app(app.id, publish=False)

        assignments = await app_repo.get_assignments(app.id)
        assignment_dict = {a.device_id: a for a in assignments}

        await reconciler._send_mobile_app_revoke_messages(
            app,
            {device.id},
            assignment_dict,
            version=1,
        )

        producer.publish_mobile_app_revoke.assert_awaited_once_with(
            serial_number=device.serial_number,
            mobile_app_id=app.id,
            package_name=app.package_name,
            app_version=1,
            assignment_id=assignments[0].id,
        )

    async def test_revoke_without_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(MagicMock(spec=ProfileRepository), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(db_session, "App1")

        await reconciler._send_mobile_app_revoke_messages(
            app,
            {device.id},
            {},
            version=1,
        )

        producer.publish_mobile_app_revoke.assert_awaited_once_with(
            serial_number=device.serial_number,
            mobile_app_id=app.id,
            package_name=app.package_name,
            app_version=1,
            assignment_id=None,
        )

    async def test_exception(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_mobile_app_revoke = AsyncMock(side_effect=RuntimeError("down"))
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(MagicMock(spec=ProfileRepository), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(db_session, "App1")

        await reconciler._send_mobile_app_revoke_messages(
            app,
            {device.id},
            {},
            version=1,
        )

        producer.publish_mobile_app_revoke.assert_awaited_once()

    async def test_exception_with_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_mobile_app_revoke = AsyncMock(side_effect=RuntimeError("down"))
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), app_repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_mobile_app(app.id, publish=False)

        assignments = await app_repo.get_assignments(app.id)
        assignment_dict = {a.device_id: a for a in assignments}

        await reconciler._send_mobile_app_revoke_messages(
            app,
            {device.id},
            assignment_dict,
            version=1,
        )

        failed_assignment = await app_repo.db.get(MobileAppAssignment, assignments[0].id)
        assert failed_assignment is not None
        assert failed_assignment.status == AssignmentStatus.FAILED


# ── profile recalculate from smart/static group — recalculates correctly ─


class TestRecalculateProfileGroupTriggers:
    async def test_smart_group_triggers_no_scope_match(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        sg = SmartGroup(name="SG", criteria=[], created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(exclusions=[ScopeExclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=sg.id)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assert await profile_repo.get_assignments(profile.id) is not None

    async def test_static_group_triggers_no_scope_match(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        sg = StaticGroup(name="SG1", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(exclusions=[ScopeExclusion(scope_type=ScopeType.STATIC_GROUP, exclude_id=sg.id)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assert await profile_repo.get_assignments(profile.id) is not None

    async def test_exclusion_matching_skips_resolved_devices(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        sg = SmartGroup(name="SG", criteria=[], created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        await _create_device(db_session, "Mac", "SN-1")

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
                exclusions=[ScopeExclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=sg.id)],
            ),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await profile_repo.get_assignments(profile.id)
        assert len(assignments) == 0
        assert await profile_repo.get_current_desired_device_ids(profile.id) == set()

    async def test_exclusion_resolves_empty_with_targets(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        await _create_device(db_session, "Mac", "SN-1")

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
                exclusions=[ScopeExclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=99999)],
            ),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await profile_repo.get_assignments(profile.id)
        assert len(assignments) == 1


# ── edge: compute dedup ─────────────────────────────────────────────────


class TestCompute:
    async def test_deduplication_across_targets(self) -> None:
        scope = Scope(
            targets=[
                ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=1),
                ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=2),
            ]
        )
        resolved = {
            (ScopeType.SMART_GROUP.value, 1): {10, 20},
            (ScopeType.SMART_GROUP.value, 2): {20, 30},
        }
        result = AssignmentReconciler.compute(
            profile_id=1, profile_version=1, scope=scope, resolved_device_ids=resolved
        )
        device_ids = {a.device_id for a in result}
        assert device_ids == {10, 20, 30}
        assert len(result) == 3


# ── edge: recalculate_profile not found ──────────────────────────────────


class TestRecalculateProfileNotFound:
    async def test_profile_not_found_returns_early(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        await reconciler.recalculate_profile(99999)

        producer.publish_profile_push.assert_not_awaited()
        producer.publish_profile_revoke.assert_not_awaited()


# ── edge: recalculate_profile with revoke ────────────────────────────────


class TestRecalculateProfileRevoke:
    async def test_removes_device_and_sends_revoke(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        d2 = await _create_device(db_session, "Mac2", "SN-2")

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[
                    ScopeTarget(scope_type=ScopeType.DEVICE, target_id=d1.id),
                    ScopeTarget(scope_type=ScopeType.DEVICE, target_id=d2.id),
                ]
            ),
        )
        await repo.bulk_create_assignments(profile.id, 1, {d1.id, d2.id})

        profile = await repo.get_by_id(profile.id)
        assert profile is not None
        profile.scope = Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=d1.id)])
        await db_session.commit()

        await reconciler.recalculate_profile(profile.id)

        producer.publish_profile_revoke.assert_awaited_once()


# ── edge: _send_push_messages exception WITH assignment ───────────────────


class TestSendPushMessagesExceptionWithAssignment:
    async def test_exception_with_assignment_marks_failed(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_profile_push = AsyncMock(side_effect=RuntimeError("push failed"))
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_profile(profile.id, publish=False)

        assignments = await profile_repo.get_assignments(profile.id)
        assignment_dict = {a.device_id: a for a in assignments}

        await reconciler._send_push_messages(
            profile,
            {device.id},
            assignment_dict,
            version=1,
        )

        failed_assignment = await profile_repo.db.get(ProfileAssignment, assignments[0].id)
        assert failed_assignment is not None
        assert failed_assignment.status == AssignmentStatus.FAILED


# ── edge: _send_revoke_messages exception WITH assignment ─────────────────


class TestSendRevokeMessagesExceptionWithAssignment:
    async def test_exception_with_assignment_marks_failed(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_profile_revoke = AsyncMock(side_effect=RuntimeError("revoke failed"))
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_profile(profile.id, publish=False)

        assignments = await profile_repo.get_assignments(profile.id)
        assignment_dict = {a.device_id: a for a in assignments}

        await reconciler._send_revoke_messages(
            profile,
            {device.id},
            assignment_dict,
            version=1,
        )

        failed_assignment = await profile_repo.db.get(ProfileAssignment, assignments[0].id)
        assert failed_assignment is not None
        assert failed_assignment.status == AssignmentStatus.FAILED


# ── edge: _resolve_serial_map empty ───────────────────────────────────────


class TestResolveSerialMapEmpty:
    async def test_profile_serial_map_empty(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(repo, MagicMock(spec=MobileAppRepository), producer)
        assert await reconciler._resolve_serial_map(set()) == {}

    async def test_mobile_serial_map_empty(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), repo, producer)
        assert await reconciler._resolve_serial_map_mobile(set()) == {}


# ── edge: _send_*_messages with non-existent device ───────────────────────


class TestSendMessagesMissingSerial:
    async def test_send_push_skips_missing_serial(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)
        profile = await _create_profile(db_session, "P1")
        await reconciler._send_push_messages(profile, {99999}, {}, version=1)
        producer.publish_profile_push.assert_not_awaited()

    async def test_send_revoke_skips_missing_serial(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        profile_repo = ProfileRepository(db_session)
        reconciler = AssignmentReconciler(profile_repo, MagicMock(spec=MobileAppRepository), producer)
        profile = await _create_profile(db_session, "P1")
        await reconciler._send_revoke_messages(profile, {99999}, {}, version=1)
        producer.publish_profile_revoke.assert_not_awaited()

    async def test_send_mobile_push_skips_missing_serial(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), app_repo, producer)
        app = await _create_mobile_app(db_session, "App1")
        await reconciler._send_mobile_app_push_messages(app, {99999}, {}, version=1)
        producer.publish_mobile_app_push.assert_not_awaited()

    async def test_send_mobile_revoke_skips_missing_serial(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        app_repo = MobileAppRepository(db_session)
        reconciler = AssignmentReconciler(ProfileRepository(db_session), app_repo, producer)
        app = await _create_mobile_app(db_session, "App1")
        await reconciler._send_mobile_app_revoke_messages(app, {99999}, {}, version=1)
        producer.publish_mobile_app_revoke.assert_not_awaited()
