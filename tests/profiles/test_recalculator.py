from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Exclusion, Scope, ScopeType, Target
from app.devices.models import Device
from app.messaging.producer import RabbitMQProducer
from app.profiles.models import Profile, ProfileAssignment
from app.profiles.reconciler import ProfileAssignmentReconciler
from app.profiles.repositories import ProfileRepository
from app.smart_groups.models import SmartGroup
from app.static_groups.models import StaticGroup, StaticGroupDevice


def _make_producer() -> MagicMock:
    producer = MagicMock(spec=RabbitMQProducer)
    producer.publish_profile_push = AsyncMock(return_value="msg-id")
    producer.publish_profile_revoke = AsyncMock(return_value="msg-id")
    return producer


async def _create_device(
    db: AsyncSession, name: str, serial: str, status: str = "ENROLLED"
) -> Device:
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


async def _create_profile(
    db: AsyncSession, name: str, scope: Scope | None = None
) -> Profile:
    profile = Profile(name=name, scope=scope or Scope(), policy={})
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def _create_assignment(
    db: AsyncSession, profile_id: int, device_id: int, version: int = 1
) -> ProfileAssignment:
    assignment = ProfileAssignment(
        profile_id=profile_id,
        device_id=device_id,
        profile_version=version,
    )
    db.add(assignment)
    await db.commit()
    return assignment


# ---------------------------------------------------------------------------
# recalculate_profile — basic scenarios
# ---------------------------------------------------------------------------


class TestRecalculateProfile:
    async def test_new_assignments(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1
        assert assignments[0].device_id == device.id
        assert assignments[0].profile_version == 1
        producer.publish_profile_push.assert_awaited_once()

    async def test_no_changes(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )
        await _create_assignment(db_session, profile.id, device.id)

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1
        producer.publish_profile_push.assert_not_awaited()
        producer.publish_profile_revoke.assert_not_awaited()

    async def test_force_push_reapplies_existing_assignments(
        self, db_session: AsyncSession
    ) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await _create_assignment(db_session, profile.id, device.id)

        await reconciler.recalculate_profile(profile.id, force_push=True)

        producer.publish_profile_push.assert_awaited_once_with(
            device_id=device.id,
            profile_id=profile.id,
            profile_config=profile.policy,
            profile_version=2,
            assignment_id=2,
        )

    async def test_empty_scope_clears(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        await _create_assignment(db_session, profile.id, device.id)

        await reconciler.recalculate_profile(profile.id)

        assert await repo.get_current_desired_device_ids(profile.id) == set()
        producer.publish_profile_revoke.assert_awaited_once_with(
            device_id=device.id,
            profile_id=profile.id,
            profile_version=2,
            assignment_id=2,
        )

    async def test_empty_scope_delete_is_committed(
        self, db_session: AsyncSession
    ) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        await _create_assignment(db_session, profile.id, device.id)

        await reconciler.recalculate_profile(profile.id)
        await db_session.rollback()

        fresh_repo = ProfileRepository(db_session)
        assignments = await fresh_repo.get_current_assignments(profile.id)
        assert len(assignments) == 1
        assert assignments[0].desired_state.value == "ABSENT"

    async def test_profile_not_found(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        await reconciler.recalculate_profile(99999)
        producer.publish_profile_push.assert_not_awaited()


# ---------------------------------------------------------------------------
# recalculate_profile — device add/remove
# ---------------------------------------------------------------------------


class TestRecalculateDeviceChanges:
    async def test_adds_device(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )
        await _create_assignment(db_session, profile.id, d1.id)

        d2 = await _create_device(db_session, "Mac2", "SN-2")

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        device_ids = {a.device_id for a in assignments}
        assert d1.id in device_ids
        assert d2.id in device_ids
        assert producer.publish_profile_push.await_count == 1

    async def test_removes_device(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        d2 = await _create_device(db_session, "Mac2", "SN-2")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[
                    Target(scope_type=ScopeType.DEVICE, target_id=d1.id),
                    Target(scope_type=ScopeType.DEVICE, target_id=d2.id),
                ]
            ),
        )
        await _create_assignment(db_session, profile.id, d1.id)
        await _create_assignment(db_session, profile.id, d2.id)

        profile = await repo.get_by_id(profile.id)
        assert profile is not None
        profile.scope = Scope(
            targets=[Target(scope_type=ScopeType.DEVICE, target_id=d1.id)]
        )
        await db_session.commit()

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        current = {
            a.device_id
            for a in assignments
            if a.desired_state.value == "PRESENT"
        }
        assert current == {d1.id}
        producer.publish_profile_revoke.assert_awaited_once()


# ---------------------------------------------------------------------------
# recalculate_profile — scope types
# ---------------------------------------------------------------------------


class TestRecalculateScopeTypes:
    async def test_all_devices(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        d2 = await _create_device(db_session, "Mac2", "SN-2")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        device_ids = {a.device_id for a in assignments}
        assert device_ids == {d1.id, d2.id}

    async def test_all_devices_only_includes_enrolled_devices(
        self, db_session: AsyncSession
    ) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        enrolled = await _create_device(db_session, "Enrolled", "SN-1", "ENROLLED")
        unenrolled = await _create_device(
            db_session, "Unenrolled", "SN-2", "UNENROLLED"
        )
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assert await repo.get_current_desired_device_ids(profile.id) == {enrolled.id}
        assert unenrolled.id not in await repo.get_current_desired_device_ids(profile.id)

    async def test_device_target(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        d2 = await _create_device(db_session, "Mac2", "SN-2")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.DEVICE, target_id=d1.id)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        device_ids = {a.device_id for a in assignments}
        assert device_ids == {d1.id}
        assert d2.id not in device_ids

    async def test_missing_device_target_is_ignored(
        self, db_session: AsyncSession
    ) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.DEVICE, target_id=99999)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assert await repo.get_assignments(profile.id) == []
        producer.publish_profile_push.assert_not_awaited()

    async def test_static_group(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        await _create_device(db_session, "Mac2", "SN-2")
        sg = StaticGroup(name="SG1")
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        db_session.add(StaticGroupDevice(static_group_id=sg.id, device_serial_number="SN-1"))
        await db_session.commit()

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        device_ids = {a.device_id for a in assignments}
        assert device_ids == {d1.id}

    async def test_smart_group(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        await _create_device(db_session, "MacBook Pro", "SN-1")
        await _create_device(db_session, "iPhone", "SN-2")

        sg = SmartGroup(
            name="Macs",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "Mac"}],
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1


# ---------------------------------------------------------------------------
# recalculate_profile — exclusions
# ---------------------------------------------------------------------------


class TestRecalculateExclusions:
    async def test_exclusion_removes_device(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        d2 = await _create_device(db_session, "Mac2", "SN-2")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[Target(scope_type=ScopeType.ALL_DEVICES)],
                exclusions=[Exclusion(scope_type=ScopeType.DEVICE, exclude_id=d1.id)],
            ),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        device_ids = {a.device_id for a in assignments}
        assert device_ids == {d2.id}

    async def test_all_excluded(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[Target(scope_type=ScopeType.ALL_DEVICES)],
                exclusions=[Exclusion(scope_type=ScopeType.DEVICE, exclude_id=d1.id)],
            ),
        )

        await reconciler.recalculate_profile(profile.id)

        max_version = await repo.get_max_assignment_version(profile.id)
        device_ids = await repo.get_assignment_device_ids_at_version(profile.id, max_version)
        assert len(device_ids) == 0

    async def test_smart_group_exclusion(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        await _create_device(db_session, "MacBook Pro", "SN-1")
        await _create_device(db_session, "MacBook Air", "SN-2")

        sg = SmartGroup(
            name="Macs",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "MacBook"}],
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)

        excl_sg = SmartGroup(
            name="Pros",
            criteria=[{"field": "name", "operator": "like", "type": "string", "value": "Pro"}],
        )
        db_session.add(excl_sg)
        await db_session.commit()
        await db_session.refresh(excl_sg)

        profile = await _create_profile(
            db_session,
            "P1",
            Scope(
                targets=[Target(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)],
                exclusions=[Exclusion(scope_type=ScopeType.SMART_GROUP, exclude_id=excl_sg.id)],
            ),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1


# ---------------------------------------------------------------------------
# recalculate_profile — version handling
# ---------------------------------------------------------------------------


class TestRecalculateVersion:
    async def test_first_assignment_version_1(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_profile(profile.id)

        max_version = await repo.get_max_assignment_version(profile.id)
        assert max_version == 1

    async def test_existing_version_preserved(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.DEVICE, target_id=d1.id)]),
        )
        await _create_assignment(db_session, profile.id, d1.id, version=5)

        d2 = await _create_device(db_session, "Mac2", "SN-2")
        profile = await repo.get_by_id(profile.id)
        assert profile is not None
        profile.scope = Scope(
            targets=[
                Target(scope_type=ScopeType.DEVICE, target_id=d1.id),
                Target(scope_type=ScopeType.DEVICE, target_id=d2.id),
            ]
        )
        await db_session.commit()

        await reconciler.recalculate_profile(profile.id)

        max_version = await repo.get_max_assignment_version(profile.id)
        assert max_version == 6
        assert len(await repo.get_current_assignments(profile.id)) == 2

    async def test_no_version_when_no_assignments(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)

        profile = await _create_profile(db_session, "P1")
        max_version = await repo.get_max_assignment_version(profile.id)
        assert max_version == 0


# ---------------------------------------------------------------------------
# recalculate_for_device
# ---------------------------------------------------------------------------


class TestRecalculateForDevice:
    async def test_triggers_all_profiles(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        p1 = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )
        p2 = await _create_profile(
            db_session,
            "P2",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )
        await _create_profile(db_session, "P3")

        await reconciler.recalculate_for_device(device.id)

        a1 = await repo.get_assignments(p1.id)
        a2 = await repo.get_assignments(p2.id)
        assert len(a1) == 1
        assert len(a2) == 1

    async def test_no_profiles_with_scope(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        await _create_profile(db_session, "P1")

        await reconciler.recalculate_for_device(device.id)
        producer.publish_profile_push.assert_not_awaited()


# ---------------------------------------------------------------------------
# Message sending
# ---------------------------------------------------------------------------


class TestMessageSending:
    async def test_push_for_new_assignments(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_profile(profile.id)

        producer.publish_profile_push.assert_awaited_once_with(
            device_id=device.id,
            profile_id=profile.id,
            profile_config=profile.policy,
            profile_version=1,
            assignment_id=1,
        )

    async def test_revoke_for_removed_assignments(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        d1 = await _create_device(db_session, "Mac1", "SN-1")
        d2 = await _create_device(db_session, "Mac2", "SN-2")

        # Scope targets only d1
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.DEVICE, target_id=d1.id)]),
        )

        # Pre-create an assignment for d2 (stale — d2 is not in scope)
        await _create_assignment(db_session, profile.id, d2.id)

        await reconciler.recalculate_profile(profile.id)

        producer.publish_profile_revoke.assert_awaited_once_with(
            device_id=d2.id,
            profile_id=profile.id,
            profile_version=2,
            assignment_id=3,
        )

    async def test_message_failure_does_not_crash(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_profile_push = AsyncMock(side_effect=RuntimeError("RabbitMQ down"))
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
        )

        await reconciler.recalculate_profile(profile.id)

        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1

        assert assignments[0].status == "FAILED"
        assert assignments[0].attempt_count == 1
        assert assignments[0].last_error == "RabbitMQ down"

    async def test_check_in_reconciles_latest_desired_revision(
        self, db_session: AsyncSession
    ) -> None:
        producer = _make_producer()
        repo = ProfileRepository(db_session)
        reconciler = ProfileAssignmentReconciler(repo, producer)

        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[Target(scope_type=ScopeType.DEVICE, target_id=device.id)]),
        )
        await reconciler.recalculate_profile(profile.id)
        producer.publish_profile_push.reset_mock()

        await reconciler.reconcile_device(device.id)

        producer.publish_profile_push.assert_awaited_once()
        assignment = (await repo.get_current_assignments(profile.id))[0]
        assert assignment.status == "SENT"
        assert assignment.attempt_count == 2
