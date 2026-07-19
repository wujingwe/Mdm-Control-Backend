#!/usr/bin/env python3
"""Seed the database with sample data for end-to-end testing.

Usage:
  cd /Users/jing-weiwu/Projects/MdM-Control-Backend
  venv/bin/python seed.py
"""

import asyncio
from datetime import datetime, timezone

from app.database import async_session, engine
from app.devices.models import Device
from app.smart_groups.models import SmartGroup
from app.static_groups.models import StaticGroup
from app.users.models import User
from app.devices.schemas import Network, Wifi
from passlib.context import CryptContext
from sqlalchemy import text

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEVICES = [
    Device(
        name="SM-G998B-001",
        serial_number="RZCR80GJ0JH",
        os_version="Android 14",
        connection_status="Online",
        status="Compliant",
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
        connection_status="Online",
        status="Compliant",
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
        connection_status="Online",
        status="Compliant",
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
        connection_status="Online",
        status="Non-compliant",
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
        connection_status="Offline",
        status="Needs attention",
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
        connection_status="Online",
        status="Compliant",
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
        connection_status="Online",
        status="Compliant",
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
        connection_status="Pending",
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
        connection_status="Offline",
        status="Non-compliant",
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
        connection_status="Online",
        status="Compliant",
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
        connection_status="Online",
        status="Needs attention",
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
        connection_status="Offline",
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
        connection_status="Online",
        status="Compliant",
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
        connection_status="Online",
        status="Compliant",
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
        connection_status="Pending",
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


async def seed():
    async with async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        if result.scalar() and result.scalar() > 0:
            print("Database already seeded.")
            return

        hash_pw = pwd_context.hash("password")
        now = datetime.now(timezone.utc)
        users = [
            User(
                email="admin@example.com",
                name="Admin User",
                password_hash=hash_pw,
                permissions=["admin"],
                created_at=now,
                last_login=now,
            ),
            User(
                email="jane@example.com",
                name="Jane Editor",
                password_hash=hash_pw,
                permissions=["editor"],
                created_at=now,
            ),
            User(
                email="bob@example.com",
                name="Bob Viewer",
                password_hash=hash_pw,
                permissions=["viewer"],
                created_at=now,
            ),
        ]
        session.add_all(users)
        await session.flush()

        session.add_all(DEVICES)
        await session.flush()

        session.add_all(SMART_GROUPS)
        await session.flush()

        session.add_all(STATIC_GROUPS)
        await session.flush()

        await session.commit()

    await engine.dispose()
    print("Database seeded:")
    print("  3 users, 15 devices, 3 smart groups, 2 static groups")


if __name__ == "__main__":
    asyncio.run(seed())
