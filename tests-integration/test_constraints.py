"""DB-level constraint enforcement (MariaDB).

SQLite only enforces FK/NOT NULL in some configurations and ignores VARCHAR
lengths and enum checks, so these constraints are verified only against the
real database.
"""

import pytest
from sqlalchemy.exc import DataError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.devices.models import Device
from app.domains.users.models import User

from helpers import create_device, create_user


class TestVarcharLength:
    async def test_serial_number_over_30_chars_rejected(self, db_session: AsyncSession) -> None:
        db_session.add(
            Device(
                name="Too Long",
                serial_number="X" * 31,
                os_version="Android 14",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        with pytest.raises(DataError):
            await db_session.flush()

    async def test_os_version_over_20_chars_rejected(self, db_session: AsyncSession) -> None:
        db_session.add(
            Device(
                name="Long OS",
                serial_number="SN-LONG-OS",
                os_version="X" * 21,
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        with pytest.raises(DataError):
            await db_session.flush()


class TestNotNull:
    async def test_device_without_name_rejected(self, db_session: AsyncSession) -> None:
        db_session.add(
            Device(
                serial_number="SN-NO-NAME",
                os_version="Android 14",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_user_without_email_rejected(self, db_session: AsyncSession) -> None:
        db_session.add(User(name="No Email"))
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestUniqueConstraint:
    async def test_duplicate_device_serial_rejected(self, db_session: AsyncSession) -> None:
        await create_device(db_session, "SN-DUP")
        await db_session.commit()

        db_session.add(
            Device(
                name="Duplicate",
                serial_number="SN-DUP",
                os_version="Android 14",
                connection_status=ConnectionStatus.CONNECTED,
                status=DeviceStatus.ENROLLED,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_duplicate_user_email_rejected(self, db_session: AsyncSession) -> None:
        await create_user(db_session, email="dup@test.local")
        await db_session.commit()

        db_session.add(User(email="dup@test.local", name="Duplicate"))
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestDatetimeColumn:
    async def test_device_without_last_enrolled_at_defaults(self, db_session: AsyncSession) -> None:
        device = Device(
            name="No Enroll Date",
            serial_number="SN-NO-ENROLL",
            os_version="Android 14",
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
        )
        db_session.add(device)
        await db_session.commit()
        assert device.last_enrolled_at is not None


class TestEnumCheck:
    """DB-level enum enforcement via CHECK constraints.

    Values are inserted with raw SQL to bypass the ORM's Python-side Enum
    validation, proving the database itself rejects invalid enum values.
    """

    async def test_invalid_device_connection_status_rejected(self, db_session: AsyncSession) -> None:
        with pytest.raises(OperationalError):
            await db_session.execute(
                text(
                    "INSERT INTO devices "
                    "(name, serial_number, os_version, connection_status, status, last_enrolled_at, created_at, updated_at) "
                    "VALUES (:name, :serial_number, :os, 'BOGUS', 'ENROLLED', NOW(), NOW(), NOW())"
                ),
                {"name": "Bad", "serial_number": "SN-BAD-STATUS", "os": "Android 14"},
            )

    async def test_invalid_device_status_rejected(self, db_session: AsyncSession) -> None:
        with pytest.raises(OperationalError):
            await db_session.execute(
                text(
                    "INSERT INTO devices "
                    "(name, serial_number, os_version, connection_status, status, last_enrolled_at, created_at, updated_at) "
                    "VALUES (:name, :serial_number, :os, 'CONNECTED', 'BOGUS', NOW(), NOW(), NOW())"
                ),
                {"name": "Bad", "serial_number": "SN-BAD-CONN", "os": "Android 14"},
            )

    async def test_invalid_command_status_rejected(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session, email="cmd@test.local")
        device = await create_device(db_session, "SN-CMD-BAD")
        await db_session.commit()
        with pytest.raises(OperationalError):
            await db_session.execute(
                text(
                    "INSERT INTO commands (device_id, command_type, status, created_by, created_at) "
                    "VALUES (:device_id, 'LOCK', 'BOGUS', :created_by, NOW())"
                ),
                {"device_id": device.id, "created_by": user.id},
            )

    async def test_invalid_extension_data_type_rejected(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session, email="ext@test.local")
        await db_session.commit()
        with pytest.raises(OperationalError):
            await db_session.execute(
                text(
                    "INSERT INTO extension_attributes "
                    "(name, data_type, input_type, created_by, created_at, updated_at) "
                    "VALUES ('Bad', 'BOGUS', 'TEXT_FIELD', :created_by, NOW(), NOW())"
                ),
                {"created_by": user.id},
            )
