import logging
from datetime import datetime, timezone

from passlib.context import CryptContext
from sqlalchemy import text

from app.database import engine, async_session
from app.base import Base
from app.devices.models import Device
from app.extension_attributes.models import ExtensionAttribute
from app.inventory_search.models import InventorySearch
from app.profiles.models import Profile
from app.profiles.profile_scope import ProfileScope
from app.smart_groups.models import SmartGroup
from app.static_groups.models import StaticGroup
from app.static_groups.static_group_device import StaticGroupDevice
from app.users.models import User
from app.devices.schemas import Network, Wifi

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEVICES = [
    Device(
        name="SM-G998B-001", serial_number="RZCR80GJ0JH",
        os_version="Android 14", connection_status="Online", enrollment_status="Compliant",
        battery_status=85,
        total_storage=256, available_storage=180, total_memory=12, available_memory=6,
        network=Network(wifi=Wifi(ssid="Office")),
    ),
    Device(
        name="SM-F936B-002", serial_number="R3CT90J0JH",
        os_version="Android 14", connection_status="Online", enrollment_status="Compliant",
        battery_status=62,
        total_storage=512, available_storage=410, total_memory=12, available_memory=8,
    ),
    Device(
        name="Pixel-8-Pro-003", serial_number="PIX8A0J0JH",
        os_version="Android 15", connection_status="Online", enrollment_status="Compliant",
        battery_status=91,
        total_storage=128, available_storage=95, total_memory=8, available_memory=4,
    ),
    Device(
        name="SM-S901B-004", serial_number="RZCT80G0JH",
        os_version="Android 13", connection_status="Online", enrollment_status="Non-compliant",
        battery_status=45,
        total_storage=128, available_storage=60, total_memory=8, available_memory=2,
    ),
    Device(
        name="OnePlus-12-005", serial_number="OP12A0J0JH",
        os_version="Android 14", connection_status="Offline", enrollment_status="Needs attention",
        battery_status=12,
        total_storage=256, available_storage=200, total_memory=16, available_memory=10,
    ),
    Device(
        name="SM-A546B-006", serial_number="RZCT60G0JH",
        os_version="Android 14", connection_status="Online", enrollment_status="Compliant",
        battery_status=78,
        total_storage=256, available_storage=190, total_memory=8, available_memory=5,
    ),
    Device(
        name="Pixel-7-007", serial_number="PIX7A0J0JH",
        os_version="Android 14", connection_status="Online", enrollment_status="Compliant",
        battery_status=95,
        total_storage=128, available_storage=100, total_memory=8, available_memory=5,
    ),
    Device(
        name="SM-X906B-008", serial_number="RZCT80G1JH",
        os_version="Android 14", connection_status="Pending", enrollment_status="Pending",
        battery_status=30,
        total_storage=512, available_storage=480, total_memory=12, available_memory=9,
    ),
    Device(
        name="SM-G990B2-009", serial_number="RZCT90G2JH",
        os_version="Android 13", connection_status="Offline", enrollment_status="Non-compliant",
        battery_status=0,
        total_storage=64, available_storage=20, total_memory=6, available_memory=1,
    ),
    Device(
        name="Pixel-6a-010", serial_number="PIX6A0J0JH",
        os_version="Android 13", connection_status="Online", enrollment_status="Compliant",
        battery_status=72,
        total_storage=128, available_storage=85, total_memory=6, available_memory=3,
    ),
    Device(
        name="OnePlus-11-011", serial_number="OP11A0J0JH",
        os_version="Android 14", connection_status="Online", enrollment_status="Needs attention",
        battery_status=55,
        total_storage=256, available_storage=120, total_memory=16, available_memory=7,
    ),
    Device(
        name="SM-S928B-012", serial_number="RZCT95G0JH",
        os_version="Android 14", connection_status="Offline", enrollment_status="Unknown",
        battery_status=8,
        total_storage=256, available_storage=230, total_memory=12, available_memory=10,
    ),
    Device(
        name="Moto-G85-013", serial_number="MOTG85J0JH",
        os_version="Android 14", connection_status="Online", enrollment_status="Compliant",
        battery_status=88,
        total_storage=128, available_storage=75, total_memory=8, available_memory=4,
    ),
    Device(
        name="Pixel-9-Pro-014", serial_number="PIX9A0J0JH",
        os_version="Android 15", connection_status="Online", enrollment_status="Compliant",
        battery_status=76,
        total_storage=512, available_storage=420, total_memory=16, available_memory=10,
    ),
    Device(
        name="SM-F721B-015", serial_number="RZCT85G0JH",
        os_version="Android 13", connection_status="Pending", enrollment_status="Pending",
        battery_status=40,
        total_storage=128, available_storage=50, total_memory=8, available_memory=3,
    ),
]

SMART_GROUPS = [
    SmartGroup(
        name="All Android 14 Devices",
        description="Smart group that includes all devices running Android 14",
        created_by=1,
        criteria=[
            {"criteria": "os_version", "operator": "is", "type": "string", "value": "Android 14", "left_parentheses": False, "right_parentheses": False},
        ],
    ),
    SmartGroup(
        name="Non-compliant Devices",
        description="Smart group tracking all non-compliant devices",
        created_by=1,
        criteria=[
            {"criteria": "compliance", "operator": "is", "type": "string", "value": "Non-compliant", "left_parentheses": False, "right_parentheses": False},
        ],
    ),
    SmartGroup(
        name="Critical Issues",
        description="Devices needing immediate attention",
        created_by=1,
        criteria=[
            {"criteria": "compliance", "operator": "is", "type": "string", "value": "Needs attention", "left_parentheses": True, "right_parentheses": False},
            {"criteria": "battery_level", "operator": "lessThan", "type": "number", "value": "15", "left_parentheses": False, "right_parentheses": True},
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
            {"criteria": "connection_status", "operator": "is", "type": "string", "value": "Online", "left_parentheses": False, "right_parentheses": False},
            {"criteria": "os_version", "operator": "is", "type": "string", "value": "Android 14", "left_parentheses": False, "right_parentheses": False},
        ],
        created_by=1,
    ),
    InventorySearch(
        name="Low Battery Devices",
        description="Devices with battery below 20%",
        criteria=[
            {"criteria": "battery_status", "operator": "lessThan", "type": "number", "value": "20", "left_parentheses": False, "right_parentheses": False},
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
        settings={
            "passwordPolicy": {"minLength": 6, "requireAlphanumeric": True},
            "encryptionRequired": True,
            "allowAppInstallation": True,
        },
        created_by=1,
    ),
    Profile(
        name="Executive Security",
        description="Enhanced security profile for executive devices",
        version=1,
        settings={
            "passwordPolicy": {"minLength": 10, "requireComplexity": True},
            "encryptionRequired": True,
            "allowAppInstallation": False,
            "allowScreenCapture": False,
            "allowBluetooth": False,
        },
        created_by=1,
    ),
]

PROFILE_SCOPES = [
    {"profile_index": 0, "target_type": "ALL_DEVICES", "target_id": None},
    {"profile_index": 1, "target_type": "SMART_GROUP", "target_id": None},
]


async def seed_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar() or 0
        if user_count > 0:
            logger.info("Mock database already seeded, skipping.")
            return

        hash_pw = pwd_context.hash("password")
        now = datetime.now(timezone.utc)
        users = [
            User(email="admin@example.com", name="Admin User", password_hash=hash_pw,
                 permissions=["admin"], created_at=now, last_login=now),
            User(email="jane@example.com", name="Jane Editor", password_hash=hash_pw,
                 permissions=["editor"], created_at=now),
            User(email="bob@example.com", name="Bob Viewer", password_hash=hash_pw,
                 permissions=["viewer"], created_at=now),
        ]
        session.add_all(users)
        await session.flush()

        session.add_all(DEVICES)
        await session.flush()

        session.add_all(SMART_GROUPS)
        await session.flush()
        smart_group_ids = [sg.id for sg in SMART_GROUPS]

        session.add_all(STATIC_GROUPS)
        await session.flush()
        static_group_ids = [sg.id for sg in STATIC_GROUPS]

        device_ids = [d.id for d in DEVICES]
        if len(static_group_ids) >= 2:
            session.add(StaticGroupDevice(static_group_id=static_group_ids[0], device_id=device_ids[0]))
            session.add(StaticGroupDevice(static_group_id=static_group_ids[0], device_id=device_ids[2]))
            session.add(StaticGroupDevice(static_group_id=static_group_ids[0], device_id=device_ids[13]))
            session.add(StaticGroupDevice(static_group_id=static_group_ids[1], device_id=device_ids[3]))
            session.add(StaticGroupDevice(static_group_id=static_group_ids[1], device_id=device_ids[4]))

        session.add_all(INVENTORY_SEARCHES)

        session.add_all(EXTENSION_ATTRIBUTES)

        session.add_all(PROFILES)
        await session.flush()
        profile_ids = [p.id for p in PROFILES]

        if profile_ids and smart_group_ids:
            session.add(ProfileScope(profile_id=profile_ids[0], target_type="ALL_DEVICES"))
            session.add(ProfileScope(profile_id=profile_ids[1], target_type="SMART_GROUP", target_id=smart_group_ids[0]))

        await session.commit()

    logger.info("Mock database seeded with 3 users, 15 devices, 3 smart groups, 2 static groups, 2 inventory searches, 3 extension attributes, 2 profiles")
