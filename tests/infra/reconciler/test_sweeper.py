from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.enums import DeviceStatus
from app.domains.devices.models import Device
from app.domains.devices.repositories import DeviceRepository
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.profiles.models import Profile, ProfileAssignment
from app.domains.profiles.repositories import ProfileRepository
from app.domains.smart_groups.repositories import SmartGroupRepository
from app.domains.shared.scope import Scope
from app.infra.messaging.producer import RabbitMQProducer
from app.infra.reconciler.reconciler import AssignmentReconciler, SweepResult

ONE_HOUR = timedelta(hours=1)


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


async def _create_profile(db: AsyncSession, name: str) -> Profile:
    profile = Profile(name=name, scope=Scope(), policy={}, created_by=1)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def _create_mobile_app(db: AsyncSession, name: str, package_name: str = "com.test.app") -> MobileApp:
    app = MobileApp(
        name=name,
        package_name=package_name,
        package_version="1.0.0",
        version=1,
        scope=Scope(),
        created_by=1,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


def _reconciler(db: AsyncSession, producer: MagicMock) -> AssignmentReconciler:
    return AssignmentReconciler(
        ProfileRepository(db),
        MobileAppRepository(db),
        DeviceRepository(db),
        SmartGroupRepository(db),
        producer,
    )


async def _make_profile_assignment(
    db: AsyncSession,
    profile_id: int,
    device_id: int,
    *,
    status: AssignmentStatus,
    desired_state: AssignmentDesiredState = AssignmentDesiredState.PRESENT,
    profile_version: int = 1,
    attempt_count: int = 1,
    last_attempt_at: datetime | None = None,
) -> ProfileAssignment:
    assignment = ProfileAssignment(
        profile_id=profile_id,
        device_id=device_id,
        status=status,
        desired_state=desired_state,
        profile_version=profile_version,
        attempt_count=attempt_count,
        last_attempt_at=last_attempt_at,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def _make_mobile_app_assignment(
    db: AsyncSession,
    mobile_app_id: int,
    device_id: int,
    *,
    status: AssignmentStatus,
    desired_state: AssignmentDesiredState = AssignmentDesiredState.PRESENT,
    version: int = 1,
    attempt_count: int = 1,
    last_attempt_at: datetime | None = None,
) -> MobileAppAssignment:
    assignment = MobileAppAssignment(
        mobile_app_id=mobile_app_id,
        device_id=device_id,
        status=status,
        desired_state=desired_state,
        version=version,
        attempt_count=attempt_count,
        last_attempt_at=last_attempt_at,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


# ── _is_due ──────────────────────────────────────────────────────────────


class TestIsDue:
    def test_never_attempted_is_due(self) -> None:
        assignment = ProfileAssignment(
            attempt_count=0,
            last_attempt_at=None,
        )
        assert AssignmentReconciler._is_due(assignment, datetime.now(timezone.utc)) is True

    def test_exhausted_budget_not_due(self) -> None:
        assignment = ProfileAssignment(
            attempt_count=5,
            last_attempt_at=datetime.now(timezone.utc) - ONE_HOUR,
        )
        assert AssignmentReconciler._is_due(assignment, datetime.now(timezone.utc)) is False

    def test_backoff_not_elapsed_not_due(self) -> None:
        now = datetime.now(timezone.utc)
        assignment = ProfileAssignment(attempt_count=1, last_attempt_at=now)
        assert AssignmentReconciler._is_due(assignment, now) is False

    def test_backoff_elapsed_is_due(self) -> None:
        now = datetime.now(timezone.utc)
        assignment = ProfileAssignment(
            attempt_count=1,
            last_attempt_at=now - timedelta(minutes=10),
        )
        assert AssignmentReconciler._is_due(assignment, now) is True


# ── sweep_stale_assignments ──────────────────────────────────────────────


class TestSweepStaleAssignments:
    async def test_resends_failed_profile_push_and_marks_sent(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        reconciler = _reconciler(db_session, producer)
        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        old = datetime.now(timezone.utc) - ONE_HOUR
        assignment = await _make_profile_assignment(
            db_session,
            profile.id,
            device.id,
            status=AssignmentStatus.FAILED,
            attempt_count=1,
            last_attempt_at=old,
        )

        result = await reconciler.sweep_stale_assignments()

        assert result == SweepResult(profile_push_sent=1)
        producer.publish_profile_push.assert_awaited_once_with(
            serial_number=device.serial_number,
            profile_id=profile.id,
            profile_config=profile.policy,
            profile_version=1,
            assignment_id=assignment.id,
        )
        await db_session.refresh(assignment)
        assert assignment.status == AssignmentStatus.SENT
        assert assignment.attempt_count == 2
        assert assignment.last_error is None

    async def test_resends_revoke_for_absent_assignment(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        reconciler = _reconciler(db_session, producer)
        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        await _make_profile_assignment(
            db_session,
            profile.id,
            device.id,
            status=AssignmentStatus.REVOKE_PENDING,
            desired_state=AssignmentDesiredState.ABSENT,
            attempt_count=1,
            last_attempt_at=datetime.now(timezone.utc) - ONE_HOUR,
        )

        result = await reconciler.sweep_stale_assignments()

        assert result.profile_revoke_sent == 1
        producer.publish_profile_revoke.assert_awaited_once()

    async def test_skips_terminal_statuses(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        reconciler = _reconciler(db_session, producer)
        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        await _make_profile_assignment(
            db_session,
            profile.id,
            device.id,
            status=AssignmentStatus.APPLIED,
            attempt_count=1,
            last_attempt_at=datetime.now(timezone.utc) - ONE_HOUR,
        )

        result = await reconciler.sweep_stale_assignments()

        assert result == SweepResult()
        producer.publish_profile_push.assert_not_awaited()
        producer.publish_profile_revoke.assert_not_awaited()

    async def test_only_current_revision_is_resent(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        reconciler = _reconciler(db_session, producer)
        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        stale = await _make_profile_assignment(
            db_session,
            profile.id,
            device.id,
            status=AssignmentStatus.FAILED,
            profile_version=1,
            attempt_count=1,
            last_attempt_at=datetime.now(timezone.utc) - ONE_HOUR,
        )
        current = await _make_profile_assignment(
            db_session,
            profile.id,
            device.id,
            status=AssignmentStatus.PENDING,
            profile_version=2,
            attempt_count=0,
            last_attempt_at=None,
        )
        profile.version = 2
        await db_session.commit()

        result = await reconciler.sweep_stale_assignments()

        assert result.profile_push_sent == 1
        producer.publish_profile_push.assert_awaited_once()
        call_kwargs = producer.publish_profile_push.await_args.kwargs
        assert call_kwargs["assignment_id"] == current.id
        assert call_kwargs["profile_version"] == 2
        assert call_kwargs["assignment_id"] != stale.id

    async def test_respects_backoff_window(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        reconciler = _reconciler(db_session, producer)
        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        await _make_profile_assignment(
            db_session,
            profile.id,
            device.id,
            status=AssignmentStatus.SENT,
            attempt_count=1,
            last_attempt_at=datetime.now(timezone.utc) - timedelta(seconds=30),
        )

        result = await reconciler.sweep_stale_assignments()

        assert result == SweepResult()
        producer.publish_profile_push.assert_not_awaited()

    async def test_counts_exhausted_rows_as_gave_up(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        reconciler = _reconciler(db_session, producer)
        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        await _make_profile_assignment(
            db_session,
            profile.id,
            device.id,
            status=AssignmentStatus.SENT,
            attempt_count=5,
            last_attempt_at=datetime.now(timezone.utc) - ONE_HOUR,
        )

        result = await reconciler.sweep_stale_assignments()

        assert result.gave_up == 1
        producer.publish_profile_push.assert_not_awaited()

    async def test_resends_mobile_app_push(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        reconciler = _reconciler(db_session, producer)
        device = await _create_device(db_session, "Mac", "SN-1")
        app = await _create_mobile_app(db_session, "App1")
        assignment = await _make_mobile_app_assignment(
            db_session,
            app.id,
            device.id,
            status=AssignmentStatus.FAILED,
            attempt_count=1,
            last_attempt_at=datetime.now(timezone.utc) - ONE_HOUR,
        )

        result = await reconciler.sweep_stale_assignments()

        assert result.mobile_app_push_sent == 1
        producer.publish_mobile_app_push.assert_awaited_once_with(
            serial_number=device.serial_number,
            mobile_app_id=app.id,
            package_name=app.package_name,
            package_version=app.package_version,
            app_version=1,
            assignment_id=assignment.id,
        )

    async def test_marks_failed_publish_and_counts_failure(self, db_session: AsyncSession) -> None:
        producer = _make_producer()
        producer.publish_profile_push = AsyncMock(side_effect=RuntimeError("broker down"))
        reconciler = _reconciler(db_session, producer)
        device = await _create_device(db_session, "Mac", "SN-1")
        profile = await _create_profile(db_session, "P1")
        assignment = await _make_profile_assignment(
            db_session,
            profile.id,
            device.id,
            status=AssignmentStatus.FAILED,
            attempt_count=1,
            last_attempt_at=datetime.now(timezone.utc) - ONE_HOUR,
        )

        result = await reconciler.sweep_stale_assignments()

        assert result.profile_push_failed == 1
        await db_session.refresh(assignment)
        assert assignment.status == AssignmentStatus.FAILED
        assert assignment.attempt_count == 2
        assert "broker down" in (assignment.last_error or "")
