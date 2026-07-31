from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.models import Device
from app.domains.devices.enums import DeviceStatus
from app.domains.mobile_apps.models import MobileApp
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.models import Profile
from app.domains.profiles.repositories import ProfileRepository
from app.domains.shared.reconciliation_service import ReconciliationService
from app.domains.shared.scope import Scope, ScopeTarget, ScopeType
from app.infra.messaging import reconciliation


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


class TestRecalculateProfilesForDevice:
    async def test_triggers_affected_profiles(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ReconciliationService(ProfileRepository(db_session), MobileAppRepository(db_session))

        device = await _create_device(db_session, "Mac", "SN-1")
        p1 = await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        )
        p2 = await _create_profile(
            db_session,
            "P2",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        )
        await _create_profile(db_session, "P3")

        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await service.recalculate_profiles_for_device(device.id)

        assert mock_publish.await_count == 2
        mock_publish.assert_any_await(
            {"entity_id": p1.id, "force_push": False},
            queue=reconciliation._profile_queue,
        )
        mock_publish.assert_any_await(
            {"entity_id": p2.id, "force_push": False},
            queue=reconciliation._profile_queue,
        )

    async def test_no_affected_profiles(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ReconciliationService(ProfileRepository(db_session), MobileAppRepository(db_session))

        device = await _create_device(db_session, "Mac", "SN-1")
        await _create_profile(db_session, "P1")

        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await service.recalculate_profiles_for_device(device.id)
        mock_publish.assert_not_awaited()


class TestRecalculateMobileAppsForDevice:
    async def test_triggers_affected_apps(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ReconciliationService(ProfileRepository(db_session), MobileAppRepository(db_session))

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
        await _create_mobile_app(db_session, "App3")

        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await service.recalculate_mobile_apps_for_device(device.id)

        assert mock_publish.await_count == 2
        mock_publish.assert_any_await(
            {"entity_id": app1.id, "force_push": False},
            queue=reconciliation._mobile_app_queue,
        )
        mock_publish.assert_any_await(
            {"entity_id": app2.id, "force_push": False},
            queue=reconciliation._mobile_app_queue,
        )

    async def test_no_affected_apps(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ReconciliationService(ProfileRepository(db_session), MobileAppRepository(db_session))

        device = await _create_device(db_session, "Mac", "SN-1")
        await _create_mobile_app(db_session, "App1")

        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await service.recalculate_mobile_apps_for_device(device.id)
        mock_publish.assert_not_awaited()


class TestRecalculateProfilesForSmartGroup:
    async def test_no_match_does_nothing(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ReconciliationService(ProfileRepository(db_session), MobileAppRepository(db_session))

        await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=999)]),
        )

        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await service.recalculate_profiles_for_group(ScopeType.SMART_GROUP, 888)

        mock_publish.assert_not_awaited()


class TestRecalculateProfilesForStaticGroup:
    async def test_no_match_does_nothing(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ReconciliationService(ProfileRepository(db_session), MobileAppRepository(db_session))

        await _create_profile(
            db_session,
            "P1",
            Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=999)]),
        )

        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await service.recalculate_profiles_for_group(ScopeType.STATIC_GROUP, 888)

        mock_publish.assert_not_awaited()


class TestRecalculateMobileAppsForSmartGroup:
    async def test_no_match_does_nothing(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ReconciliationService(ProfileRepository(db_session), MobileAppRepository(db_session))

        await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=999)]),
        )

        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await service.recalculate_mobile_apps_for_group(ScopeType.SMART_GROUP, 888)

        mock_publish.assert_not_awaited()


class TestRecalculateMobileAppsForStaticGroup:
    async def test_no_match_does_nothing(self, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
        service = ReconciliationService(ProfileRepository(db_session), MobileAppRepository(db_session))

        await _create_mobile_app(
            db_session,
            "App1",
            scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=999)]),
        )

        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await service.recalculate_mobile_apps_for_group(ScopeType.STATIC_GROUP, 888)

        mock_publish.assert_not_awaited()
