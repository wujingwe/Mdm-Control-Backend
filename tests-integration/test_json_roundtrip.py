"""JSON-column round-trips against the real database.

SQLite's JSON type is backed by TEXT and does not exercise the dialect's
native JSON binding, so these tests confirm the JSON columns survive the real
MariaDB driver round-trip (dict in -> JSON column -> dict/obj out).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.models import Device
from app.domains.devices.schemas import Certificate, Network, Wifi
from app.domains.mobile_apps.models import MobileApp
from app.domains.profiles.models import Profile
from app.domains.profiles.schemas.policy import Policy
from app.domains.shared.scope import Scope, ScopeTarget, ScopeType
from app.domains.users.models import User

from helpers import create_mobile_app, create_user


class TestProfileJson:
    async def test_policy_and_scope_round_trip(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        policy = Policy(screenCaptureDisabled=True, addUserDisabled=True, installAppsDisabled=True)
        scope = Scope(
            targets=[
                ScopeTarget(scope_type=ScopeType.ALL_DEVICES),
                ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=42),
            ]
        )
        profile = Profile(
            name="JSON Roundtrip",
            description="policy/scope roundtrip",
            policy=policy,
            scope=scope,
            created_by=user.id,
        )
        db_session.add(profile)
        await db_session.commit()

        fresh = await db_session.get(Profile, profile.id)
        assert fresh is not None
        assert fresh.policy == policy
        assert fresh.scope == scope
        assert fresh.scope.targets[1].target_id == 42

    async def test_mobile_app_scope_round_trip(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        app = await create_mobile_app(db_session, created_by=user.id)
        await db_session.commit()

        fresh = await db_session.get(MobileApp, app.id)
        assert fresh is not None
        assert fresh.scope == Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)])


class TestDeviceJson:
    async def test_network_and_certificates_round_trip(self, db_session: AsyncSession) -> None:
        network = Network(
            wifi=Wifi(ssid="CorpNet", bssid="aa:bb:cc:dd:ee:ff", signal_strength=4),
        )
        certificates = [
            Certificate(
                common_name="mdm.corp",
                issuer="Corp CA",
                expiry="2030-01-01",
                type="TLS",
                fingerprint="ab:cd:ef",
                serial_number="CERT-1",
            ),
            Certificate(
                common_name="mdm.corp",
                issuer="Corp CA",
                expiry="2030-01-01",
                type="SCEP",
                fingerprint="12:34:56",
                serial_number="CERT-2",
            ),
        ]
        device = Device(
            name="JSON Device",
            serial_number="SN-JSON",
            os_version="Android 14",
            connection_status="Connected",
            status="Enrolled",
            network=network,
            certificates=certificates,
        )
        db_session.add(device)
        await db_session.commit()

        fresh = await db_session.get(Device, device.id)
        assert fresh is not None
        assert fresh.network == network
        assert fresh.certificates == certificates


class TestUserJson:
    async def test_permissions_round_trip(self, db_session: AsyncSession) -> None:
        user = User(email="perms@test.local", name="Perm User", permissions=frozenset({"admin", "viewer"}))
        db_session.add(user)
        await db_session.commit()

        fresh = await db_session.get(User, user.id)
        assert fresh is not None
        assert fresh.permissions == frozenset({"admin", "viewer"})
