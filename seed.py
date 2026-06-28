#!/usr/bin/env python3
"""Seed the database with sample data for end-to-end testing.

Usage:
  cd /Users/jing-weiwu/Projects/MdM-Control-Backend
  venv/bin/python seed.py
"""
import asyncio
from datetime import datetime, timezone

from app.database import async_session, engine
from app.models.device import Device
from app.models.device_policy import DevicePolicy
from app.models.group import Group
from app.models.policy import Policy
from app.models.user import User
from app.schemas.device import NetworkInfo, WifiInfo
from passlib.context import CryptContext
from sqlalchemy import text

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEVICES = [
    Device(
        name="SM-G998B-001", serial_number="RZCR80GJ0JH",
        os_version="Android 14", connection_status="Online", enrollment_status="Compliant",
        battery_status=85,
        total_storage=256, available_storage=180, total_memory=12, available_memory=6,
        network=NetworkInfo(wifi=WifiInfo(ssid="Office")),
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

GROUPS = [
    Group(
        name="All Android 14 Devices",
        description="Smart group that includes all devices running Android 14",
        created_by=1, is_smart=True,
        criteria={
            "conjunction": "AND",
            "criteria": [{"field": "os_version", "operator": "is", "value": "Android 14"}],
        },
        display_columns=["name", "serial", "owner", "status", "compliance", "os_version"],
    ),
    Group(
        name="Non-compliant Devices",
        description="Smart group tracking all non-compliant devices",
        created_by=1, is_smart=True,
        criteria={
            "conjunction": "AND",
            "criteria": [{"field": "compliance", "operator": "is", "value": "Non-compliant"}],
        },
        display_columns=["name", "serial", "owner", "compliance", "last_seen"],
    ),
    Group(
        name="Critical Issues",
        description="Devices needing immediate attention",
        created_by=1, is_smart=True,
        criteria={
            "conjunction": "OR",
            "criteria": [
                {"field": "compliance", "operator": "is", "value": "Needs attention"},
                {"field": "battery_level", "operator": "lessThan", "value": "15"},
            ],
        },
        display_columns=["name", "serial", "owner", "compliance", "battery_level", "status"],
    ),
    Group(
        name="Executive Devices",
        description="Static group for executive team devices",
        created_by=1, is_smart=False,
        display_columns=["name", "serial", "owner", "status", "os_version"],
    ),
    Group(
        name="Alpha Test Group",
        description="Initial test group for policy rollout",
        created_by=1, is_smart=False,
        display_columns=["name", "serial", "status", "compliance"],
    ),
]

POLICIES = [
    Policy(
        name="Base Security Policy",
        version=2, scope="All Devices",
        rollout_state="Applied", target_devices=15, applied_devices=12,
        description="Baseline security configuration for all managed devices",
        settings={
            "cameraDisabled": False,
            "bluetoothDisabled": False,
            "debuggingFeaturesAllowed": False,
            "encryptionPolicy": "ENCRYPTION_REQUIRED",
            "passwordPolicy": {
                "minimumLength": 6,
                "quality": "ALPHABETIC",
                "maximumFailedPasswordsForWipe": 10,
            },
            "systemUpdate": {"type": "AUTOMATIC"},
        },
    ),
    Policy(
        name="Strict Compliance Policy",
        version=1, scope="Non-compliant Devices",
        rollout_state="Pushing", target_devices=3, applied_devices=1,
        description="Strict policy for non-compliant devices to enforce security standards",
        settings={
            "cameraDisabled": True,
            "bluetoothDisabled": True,
            "debuggingFeaturesAllowed": False,
            "screenCaptureDisabled": True,
            "encryptionPolicy": "ENCRYPTION_REQUIRED",
            "passwordPolicy": {
                "minimumLength": 8,
                "quality": "NUMERIC",
                "maximumFailedPasswordsForWipe": 5,
            },
        },
    ),
    Policy(
        name="Kiosk Mode Policy",
        version=3, scope="Point-of-Sale Devices",
        rollout_state="Applied", target_devices=4, applied_devices=4,
        description="Locks devices into kiosk mode for POS use cases",
        settings={
            "kioskCustomization": {
                "systemNavigation": "DISABLED",
                "statusBar": "DISABLED",
                "powerButtonActions": "POWER_OFF_MENU_ONLY",
            },
            "statusBarDisabled": True,
            "wifiConfigDisabled": True,
            "networkEscapeHatchEnabled": False,
        },
    ),
    Policy(
        name="BYOD Lightweight Policy",
        version=1, scope="Bring Your Own Device",
        rollout_state="Pending", target_devices=8, applied_devices=0,
        description="Minimal security policy for BYOD devices",
        settings={
            "cameraDisabled": False,
            "microphoneDisabled": False,
            "debuggingFeaturesAllowed": True,
            "encryptionPolicy": "ENCRYPTION_REQUIRED",
            "passwordPolicy": {
                "minimumLength": 4,
                "quality": "SIMPLE",
                "maximumFailedPasswordsForWipe": 15,
            },
            "playStoreMode": "ALLOWLIST",
        },
    ),
    Policy(
        name="Data Protection Policy",
        version=1, scope="Executive Devices",
        rollout_state="Applied", target_devices=2, applied_devices=2,
        description="Enhanced data protection for executive devices",
        settings={
            "cameraDisabled": True,
            "bluetoothDisabled": False,
            "screenCaptureDisabled": True,
            "outgoingCallsDisabled": False,
            "encryptionPolicy": "ENCRYPTION_REQUIRED",
            "passwordPolicy": {
                "minimumLength": 10,
                "quality": "COMPLEX",
                "maximumFailedPasswordsForWipe": 3,
            },
            "permissionPolicy": "DENY",
        },
    ),
]

DEVICE_POLICIES = [
    (1, 1), (2, 1), (3, 1), (4, 1), (6, 1), (7, 1), (8, 1), (10, 1), (13, 1), (15, 1),
    (5, 2), (9, 2), (12, 2),
    (11, 3),
    (14, 4),
    (1, 5), (14, 5),
]


async def seed():
    async with async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        if result.scalar() and result.scalar() > 0:
            print("Database already seeded.")
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

        session.add_all(GROUPS)
        await session.flush()

        session.add_all(POLICIES)
        await session.flush()

        for device_id, policy_id in DEVICE_POLICIES:
            session.add(DevicePolicy(device_id=device_id, policy_id=policy_id))
        await session.commit()

    await engine.dispose()
    print("Database seeded:")
    print("  3 users, 15 devices, 5 groups, 5 policies, 17 assignments")


if __name__ == "__main__":
    asyncio.run(seed())
