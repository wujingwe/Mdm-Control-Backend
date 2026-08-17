import logging
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.base import Base
from app.domains.shared.scope import Scope, ScopeTarget, ScopeType
from app.infra.core.database import engine, create_session
from app.domains.devices.models import Device, DeviceExtensionAttributeValue
from app.domains.devices.schemas import Network, Wifi
from app.domains.extension_attributes.models import ExtensionAttribute
from app.domains.inventory_search.models import InventorySearch
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.profiles.models import Profile, ProfileAssignment
from app.domains.profiles.schemas.policy import (
    BluetoothSharing,
    CameraAccess,
    DeviceConnectivityManagement,
    LocationMode,
    Policy,
    TetheringSettings,
    UsbDataAccess,
)
from app.domains.smart_groups.models import SmartGroup
from app.domains.static_groups.models import StaticGroup
from app.domains.static_groups.models import StaticGroupDevice
from app.domains.users.models import User

logger = logging.getLogger(__name__)

DEVICES = [
    Device(
        name="SM-G998B-001",
        serial_number="RZCR80GJ0JH",
        os_version="Android 14",
        connection_status="Connected",
        status="Enrolled",
        battery_status=85,
        total_storage=256,
        available_storage=180,
        total_memory=12,
        available_memory=6,
        network=Network(wifi=Wifi(ssid="Office")),
    ),
    Device(
        name="SM-F936B-002",
        serial_number="R3CT90J0JH",
        os_version="Android 14",
        connection_status="Connected",
        status="Enrolled",
        battery_status=62,
        total_storage=512,
        available_storage=410,
        total_memory=12,
        available_memory=8,
    ),
    Device(
        name="Pixel-8-Pro-003",
        serial_number="PIX8A0J0JH",
        os_version="Android 15",
        connection_status="Connected",
        status="Enrolled",
        battery_status=91,
        total_storage=128,
        available_storage=95,
        total_memory=8,
        available_memory=4,
    ),
    Device(
        name="SM-S901B-004",
        serial_number="RZCT80G0JH",
        os_version="Android 13",
        connection_status="Connected",
        status="Unenrolled",
        battery_status=45,
        total_storage=128,
        available_storage=60,
        total_memory=8,
        available_memory=2,
    ),
    Device(
        name="OnePlus-12-005",
        serial_number="OP12A0J0JH",
        os_version="Android 14",
        connection_status="Disconnected",
        status="Pending",
        battery_status=12,
        total_storage=256,
        available_storage=200,
        total_memory=16,
        available_memory=10,
    ),
    Device(
        name="SM-A546B-006",
        serial_number="RZCT60G0JH",
        os_version="Android 14",
        connection_status="Connected",
        status="Enrolled",
        battery_status=78,
        total_storage=256,
        available_storage=190,
        total_memory=8,
        available_memory=5,
    ),
    Device(
        name="Pixel-7-007",
        serial_number="PIX7A0J0JH",
        os_version="Android 14",
        connection_status="Connected",
        status="Enrolled",
        battery_status=95,
        total_storage=128,
        available_storage=100,
        total_memory=8,
        available_memory=5,
    ),
    Device(
        name="SM-X906B-008",
        serial_number="RZCT80G1JH",
        os_version="Android 14",
        connection_status="UNKNOWN",
        status="Pending",
        battery_status=30,
        total_storage=512,
        available_storage=480,
        total_memory=12,
        available_memory=9,
    ),
    Device(
        name="SM-G990B2-009",
        serial_number="RZCT90G2JH",
        os_version="Android 13",
        connection_status="Disconnected",
        status="Unenrolled",
        battery_status=0,
        total_storage=64,
        available_storage=20,
        total_memory=6,
        available_memory=1,
    ),
    Device(
        name="Pixel-6a-010",
        serial_number="PIX6A0J0JH",
        os_version="Android 13",
        connection_status="Connected",
        status="Enrolled",
        battery_status=72,
        total_storage=128,
        available_storage=85,
        total_memory=6,
        available_memory=3,
    ),
    Device(
        name="OnePlus-11-011",
        serial_number="OP11A0J0JH",
        os_version="Android 14",
        connection_status="Connected",
        status="Pending",
        battery_status=55,
        total_storage=256,
        available_storage=120,
        total_memory=16,
        available_memory=7,
    ),
    Device(
        name="SM-S928B-012",
        serial_number="RZCT95G0JH",
        os_version="Android 14",
        connection_status="Disconnected",
        status="Unknown",
        battery_status=8,
        total_storage=256,
        available_storage=230,
        total_memory=12,
        available_memory=10,
    ),
    Device(
        name="Moto-G85-013",
        serial_number="MOTG85J0JH",
        os_version="Android 14",
        connection_status="Connected",
        status="Enrolled",
        battery_status=88,
        total_storage=128,
        available_storage=75,
        total_memory=8,
        available_memory=4,
    ),
    Device(
        name="Pixel-9-Pro-014",
        serial_number="PIX9A0J0JH",
        os_version="Android 15",
        connection_status="Connected",
        status="Enrolled",
        battery_status=76,
        total_storage=512,
        available_storage=420,
        total_memory=16,
        available_memory=10,
    ),
    Device(
        name="SM-F721B-015",
        serial_number="RZCT85G0JH",
        os_version="Android 13",
        connection_status="UNKNOWN",
        status="Pending",
        battery_status=40,
        total_storage=128,
        available_storage=50,
        total_memory=8,
        available_memory=3,
    ),
]

SMART_GROUPS = [
    SmartGroup(
        name="All Android 14 Devices",
        description="Smart group that includes all devices running Android 14",
        created_by=1,
        criteria=[
            {
                "field": "os_version",
                "operator": "is",
                "type": "string",
                "value": "Android 14",
                "left_parentheses": False,
                "right_parentheses": False,
            },
        ],
    ),
    SmartGroup(
        name="Non-compliant Devices",
        description="Smart group tracking all non-compliant devices",
        created_by=1,
        criteria=[
            {
                "field": "compliance",
                "operator": "is",
                "type": "string",
                "value": "Non-compliant",
                "left_parentheses": False,
                "right_parentheses": False,
            },
        ],
    ),
    SmartGroup(
        name="Critical Issues",
        description="Devices needing immediate attention",
        created_by=1,
        criteria=[
            {
                "field": "compliance",
                "operator": "is",
                "type": "string",
                "value": "Needs attention",
                "left_parentheses": True,
                "right_parentheses": False,
            },
            {
                "field": "battery_level",
                "operator": "lessThan",
                "type": "number",
                "value": "15",
                "left_parentheses": False,
                "right_parentheses": True,
            },
        ],
    ),
]

STATIC_GROUPS = [
    StaticGroup(
        name="Executive Devices",
        description="Static group for executive team devices",
        created_by=1,
    ),
    StaticGroup(
        name="Alpha Test Group",
        description="Initial test group for profile rollout",
        created_by=1,
    ),
]

INVENTORY_SEARCHES = [
    InventorySearch(
        name="Online Android 14 Devices",
        description="Find all online devices running Android 14",
        criteria=[
            {
                "field": "connection_status",
                "operator": "is",
                "type": "string",
                "value": "Connected",
                "left_parentheses": False,
                "right_parentheses": False,
            },
            {
                "field": "os_version",
                "operator": "is",
                "type": "string",
                "value": "Android 14",
                "left_parentheses": False,
                "right_parentheses": False,
            },
        ],
        created_by=1,
    ),
    InventorySearch(
        name="Low Battery Devices",
        description="Devices with battery below 20%",
        criteria=[
            {
                "field": "battery_status",
                "operator": "lessThan",
                "type": "number",
                "value": "20",
                "left_parentheses": False,
                "right_parentheses": False,
            },
        ],
        created_by=1,
    ),
]

EXTENSION_ATTRIBUTES = [
    ExtensionAttribute(
        name="Department",
        description="The department the device is assigned to",
        data_type="string",
        input_type="Pop-up menu",
        popup_choices=["Engineering", "Sales", "Marketing", "Support", "Executive"],
        created_by=1,
    ),
    ExtensionAttribute(
        name="Asset Tag",
        description="Internal asset tracking number",
        data_type="string",
        input_type="Text field",
        created_by=1,
    ),
    ExtensionAttribute(
        name="Purchase Date",
        description="Date the device was purchased",
        data_type="date",
        input_type="Text field",
        created_by=1,
    ),
]

PROFILES = [
    Profile(
        name="Standard Compliance",
        description="Standard compliance settings for all managed devices",
        version=1,
        policy=Policy(
            locationMode=LocationMode.LOCATION_ENFORCED,
            screenCaptureDisabled=True,
            cameraAccess=CameraAccess.CAMERA_ACCESS_ENFORCED,
            deviceConnectivityManagement=DeviceConnectivityManagement(
                bluetoothSharing=BluetoothSharing.BLUETOOTH_SHARING_ALLOWED,
                tetheringSettings=TetheringSettings.ALLOW_ALL_TETHERING,
                usbDataAccess=UsbDataAccess.ALLOW_USB_DATA_TRANSFER,
            ),
        ),
        created_by=1,
    ),
    Profile(
        name="Executive Security",
        description="Enhanced security profile for executive devices",
        version=1,
        policy=Policy(
            locationMode=LocationMode.LOCATION_ENFORCED,
            screenCaptureDisabled=True,
            cameraAccess=CameraAccess.CAMERA_ACCESS_DISABLED,
            deviceConnectivityManagement=DeviceConnectivityManagement(
                bluetoothSharing=BluetoothSharing.BLUETOOTH_SHARING_DISALLOWED,
                tetheringSettings=TetheringSettings.DISALLOW_ALL_TETHERING,
                usbDataAccess=UsbDataAccess.DISALLOW_USB_DATA_TRANSFER,
            ),
        ),
        created_by=1,
    ),
]

MOBILE_APPS = [
    MobileApp(
        name="Microsoft Outlook",
        enabled=True,
        package_version="4.75.0",
        package_name="com.microsoft.office.outlook",
        scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]).model_dump(),
        created_by=1,
    ),
    MobileApp(
        name="Microsoft Teams",
        enabled=True,
        package_version="24.12.0",
        package_name="com.microsoft.teams",
        scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]).model_dump(),
        created_by=1,
    ),
]


SeedModel = TypeVar("SeedModel", bound=Base)


async def _seed_records(
    session: AsyncSession, model: type[SeedModel], records: list[SeedModel], key_attr: str
) -> list[int]:
    keys = [getattr(r, key_attr) for r in records]
    existing = set((await session.execute(select(getattr(model, key_attr)))).scalars())
    missing = [r for r in records if getattr(r, key_attr) not in existing]
    if missing:
        session.add_all(missing)
        await session.flush()
    result = await session.execute(
        select(getattr(model, "id"), getattr(model, key_attr)).where(getattr(model, key_attr).in_(keys))
    )
    by_key = {key: record_id for record_id, key in result.all()}
    return [by_key[k] for k in keys]


async def _seed_users(session: AsyncSession, now: datetime) -> None:
    existing = set((await session.execute(select(User.email))).scalars())
    users = [
        User(
            email="admin@example.com",
            name="Admin User",
            permissions=["admin"],
            created_at=now,
            last_login_at=now,
        ),
        User(
            email="jane@example.com",
            name="Jane Editor",
            permissions=["editor"],
            created_at=now,
        ),
        User(
            email="bob@example.com",
            name="Bob Viewer",
            permissions=["viewer"],
            created_at=now,
        ),
    ]
    session.add_all([u for u in users if u.email not in existing])
    await session.flush()


async def _fetch_devices_in_seed_order(session: AsyncSession) -> list[Device]:
    serials = [d.serial_number for d in DEVICES]
    result = await session.execute(select(Device).where(Device.serial_number.in_(serials)))
    by_serial = {d.serial_number: d for d in result.scalars().all()}
    return [by_serial[s] for s in serials if s in by_serial]


async def _seed_devices(session: AsyncSession) -> list[Device]:
    existing = set((await session.execute(select(Device.serial_number))).scalars())
    missing = [d for d in DEVICES if d.serial_number not in existing]
    if missing:
        session.add_all(missing)
        await session.flush()
    return await _fetch_devices_in_seed_order(session)


def _at(serials: list[str], index: int) -> str | None:
    return serials[index] if index < len(serials) else None


async def _seed_static_group_memberships(
    session: AsyncSession, static_group_ids: list[int], devices: list[Device]
) -> None:
    if len(static_group_ids) < 2:
        return
    serials = [d.serial_number for d in devices]
    candidates = [
        (static_group_ids[0], _at(serials, 0)),
        (static_group_ids[0], _at(serials, 2)),
        (static_group_ids[0], _at(serials, 13)),
        (static_group_ids[1], _at(serials, 3)),
        (static_group_ids[1], _at(serials, 4)),
    ]
    candidates = [(group_id, serial) for group_id, serial in candidates if serial is not None]
    existing = set(
        (await session.execute(select(StaticGroupDevice.static_group_id, StaticGroupDevice.device_serial_number))).all()
    )
    for group_id, serial in candidates:
        if (group_id, serial) not in existing:
            session.add(StaticGroupDevice(static_group_id=group_id, device_serial_number=serial))
    await session.flush()


async def _seed_profile_scopes(session: AsyncSession, profile_ids: list[int], smart_group_ids: list[int]) -> None:
    if not profile_ids:
        return
    scope0 = Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)])
    await session.execute(update(Profile).where(Profile.id == profile_ids[0]).values(scope=scope0.model_dump()))
    if len(profile_ids) > 1:
        scope1 = (
            Scope(
                targets=[
                    ScopeTarget(
                        scope_type=ScopeType.SMART_GROUP,
                        target_id=smart_group_ids[0] if smart_group_ids else None,
                    )
                ]
            )
            if smart_group_ids
            else Scope()
        )
        await session.execute(update(Profile).where(Profile.id == profile_ids[1]).values(scope=scope1.model_dump()))


async def _seed_extension_attribute_values(
    session: AsyncSession, devices: list[Device], ext_attribute_ids: dict[str, int]
) -> None:
    if not devices or not ext_attribute_ids:
        return
    existing = set(
        (
            await session.execute(
                select(
                    DeviceExtensionAttributeValue.device_id,
                    DeviceExtensionAttributeValue.extension_attribute_id,
                )
            )
        ).all()
    )
    rows = _build_extension_attribute_values(devices, ext_attribute_ids)
    session.add_all([row for row in rows if (row.device_id, row.extension_attribute_id) not in existing])
    await session.flush()


async def _seed_profile_assignments(
    session: AsyncSession, devices: list[Device], profile_ids: list[int], now: datetime
) -> None:
    if not devices or len(profile_ids) < 2:
        return
    existing = set((await session.execute(select(ProfileAssignment.profile_id, ProfileAssignment.device_id))).all())
    rows = _build_profile_assignments(devices, profile_ids, now)
    session.add_all([row for row in rows if (row.profile_id, row.device_id) not in existing])
    await session.flush()


async def _seed_mobile_app_assignments(
    session: AsyncSession, devices: list[Device], app_ids: list[int], now: datetime
) -> None:
    if not devices or len(app_ids) < 2:
        return
    existing = set(
        (await session.execute(select(MobileAppAssignment.mobile_app_id, MobileAppAssignment.device_id))).all()
    )
    rows = _build_mobile_app_assignments(devices, app_ids, now)
    session.add_all([row for row in rows if (row.mobile_app_id, row.device_id) not in existing])
    await session.flush()


async def seed_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(timezone.utc)

    async with create_session() as session:
        await _seed_users(session, now)
        devices = await _seed_devices(session)
        smart_group_ids = await _seed_records(session, SmartGroup, SMART_GROUPS, "name")
        static_group_ids = await _seed_records(session, StaticGroup, STATIC_GROUPS, "name")
        await _seed_static_group_memberships(session, static_group_ids, devices)
        await _seed_records(session, InventorySearch, INVENTORY_SEARCHES, "name")
        ext_attribute_ids = await _seed_records(session, ExtensionAttribute, EXTENSION_ATTRIBUTES, "name")
        ext_attribute_ids_by_name = {ea.name: ext_attribute_ids[i] for i, ea in enumerate(EXTENSION_ATTRIBUTES)}
        await _seed_extension_attribute_values(session, devices, ext_attribute_ids_by_name)
        profile_ids = await _seed_records(session, Profile, PROFILES, "name")
        await _seed_profile_scopes(session, profile_ids, smart_group_ids)
        await _seed_profile_assignments(session, devices, profile_ids, now)
        app_ids = await _seed_records(session, MobileApp, MOBILE_APPS, "package_name")
        await _seed_mobile_app_assignments(session, devices, app_ids, now)
        await session.commit()

    logger.info(
        "Mock database seeded (idempotent): users, devices, smart/static groups, inventory searches, "
        "extension attributes, profiles, mobile apps, assignments, and extension attribute values"
    )


def _build_extension_attribute_values(
    devices: list[Device], ext_attribute_ids: dict[str, int]
) -> list[DeviceExtensionAttributeValue]:
    departments = ["Engineering", "Sales", "Marketing", "Support", "Executive"]
    purchase_dates = ["2024-03-15", "2023-11-02", "2024-06-20", "2022-08-10", "2024-01-05"]
    rows: list[DeviceExtensionAttributeValue] = []
    for i, device in enumerate(devices):
        rows.append(
            DeviceExtensionAttributeValue(
                device_id=device.id,
                extension_attribute_id=ext_attribute_ids["Department"],
                extension_attribute_name="Department",
                value=departments[i % len(departments)],
            )
        )
        rows.append(
            DeviceExtensionAttributeValue(
                device_id=device.id,
                extension_attribute_id=ext_attribute_ids["Asset Tag"],
                extension_attribute_name="Asset Tag",
                value=f"AST-{1001 + i}",
            )
        )
        rows.append(
            DeviceExtensionAttributeValue(
                device_id=device.id,
                extension_attribute_id=ext_attribute_ids["Purchase Date"],
                extension_attribute_name="Purchase Date",
                value=purchase_dates[i % len(purchase_dates)],
            )
        )
    return rows


def _build_profile_assignments(devices: list[Device], profile_ids: list[int], now: datetime) -> list[ProfileAssignment]:
    standard_id, executive_id = profile_ids
    return [
        # Showcase device: two profiles with different assignment statuses.
        ProfileAssignment(
            profile_id=standard_id,
            device_id=devices[0].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
            applied_at=now,
            attempt_count=1,
            last_attempt_at=now,
        ),
        ProfileAssignment(
            profile_id=executive_id,
            device_id=devices[0].id,
            status=AssignmentStatus.REVOKE_PENDING,
            desired_state=AssignmentDesiredState.ABSENT,
            profile_version=1,
            assigned_at=now,
        ),
        ProfileAssignment(
            profile_id=standard_id,
            device_id=devices[1].id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
            message_id="msg-standard-001",
        ),
        ProfileAssignment(
            profile_id=standard_id,
            device_id=devices[2].id,
            status=AssignmentStatus.PENDING,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
        ),
        ProfileAssignment(
            profile_id=standard_id,
            device_id=devices[3].id,
            status=AssignmentStatus.FAILED,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
            attempt_count=3,
            last_attempt_at=now,
            last_error="Device did not acknowledge profile push",
        ),
        ProfileAssignment(
            profile_id=executive_id,
            device_id=devices[3].id,
            status=AssignmentStatus.PENDING,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
        ),
        ProfileAssignment(
            profile_id=executive_id,
            device_id=devices[5].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
            applied_at=now,
        ),
        ProfileAssignment(
            profile_id=standard_id,
            device_id=devices[6].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
            applied_at=now,
        ),
        ProfileAssignment(
            profile_id=executive_id,
            device_id=devices[8].id,
            status=AssignmentStatus.REVOKED,
            desired_state=AssignmentDesiredState.ABSENT,
            profile_version=1,
            assigned_at=now,
            revoked_at=now,
        ),
        ProfileAssignment(
            profile_id=standard_id,
            device_id=devices[9].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
            applied_at=now,
        ),
        ProfileAssignment(
            profile_id=standard_id,
            device_id=devices[12].id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
            message_id="msg-standard-002",
        ),
        ProfileAssignment(
            profile_id=executive_id,
            device_id=devices[13].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            profile_version=1,
            assigned_at=now,
            applied_at=now,
        ),
    ]


def _build_mobile_app_assignments(
    devices: list[Device], app_ids: list[int], now: datetime
) -> list[MobileAppAssignment]:
    outlook_id, teams_id = app_ids
    return [
        # Showcase device: two apps with different assignment statuses.
        MobileAppAssignment(
            mobile_app_id=outlook_id,
            device_id=devices[0].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
            applied_at=now,
        ),
        MobileAppAssignment(
            mobile_app_id=teams_id,
            device_id=devices[0].id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
            message_id="msg-teams-001",
        ),
        MobileAppAssignment(
            mobile_app_id=outlook_id,
            device_id=devices[5].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
            applied_at=now,
        ),
        MobileAppAssignment(
            mobile_app_id=teams_id,
            device_id=devices[5].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
            applied_at=now,
        ),
        MobileAppAssignment(
            mobile_app_id=outlook_id,
            device_id=devices[6].id,
            status=AssignmentStatus.PENDING,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
        ),
        MobileAppAssignment(
            mobile_app_id=teams_id,
            device_id=devices[9].id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
            message_id="msg-teams-002",
        ),
        MobileAppAssignment(
            mobile_app_id=outlook_id,
            device_id=devices[12].id,
            status=AssignmentStatus.SENT,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
            message_id="msg-outlook-001",
        ),
        MobileAppAssignment(
            mobile_app_id=outlook_id,
            device_id=devices[13].id,
            status=AssignmentStatus.PENDING,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
        ),
        MobileAppAssignment(
            mobile_app_id=teams_id,
            device_id=devices[13].id,
            status=AssignmentStatus.APPLIED,
            desired_state=AssignmentDesiredState.PRESENT,
            version=1,
            assigned_at=now,
            applied_at=now,
        ),
    ]


if __name__ == "__main__":
    import asyncio

    asyncio.run(seed_database())
