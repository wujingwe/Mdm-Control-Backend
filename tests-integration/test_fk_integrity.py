"""FK referential-integrity behavior on MariaDB.

The SQLite unit suite runs with FK enforcement off (the mock engine does not
turn on SQLite's PRAGMA foreign_keys), so RESTRICT/CASCADE behavior is only
exercised here against the real database.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.commands.models import Command
from app.domains.devices.models import DeviceExtensionAttributeValue
from app.domains.devices.repositories import DeviceRepository
from app.domains.extension_attributes.models import ExtensionAttribute
from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
from app.domains.mobile_apps.models import MobileAppAssignment
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.models import ProfileAssignment
from app.domains.profiles.repositories import ProfileRepository
from app.domains.static_groups.models import StaticGroupDevice
from app.domains.users.models import User
from app.domains.users.repositories import UserRepository
from app.infra.core.exceptions import ConflictError

from helpers import (
    add_command,
    add_extension_attribute_value,
    add_mobile_app_assignment,
    add_profile_assignment,
    add_static_group_device,
    create_device,
    create_extension_attribute,
    create_mobile_app,
    create_profile,
    create_static_group,
    create_user,
)


async def _count(session: AsyncSession, model, *where) -> int:
    stmt = select(func.count()).select_from(model).where(*where)
    result = await session.execute(stmt)
    return result.scalar_one()


class TestUserDeleteConflict:
    async def test_delete_user_with_referencing_content_raises_conflict(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        user_id = user.id
        await create_profile(db_session, created_by=user.id)
        await db_session.commit()

        with pytest.raises(ConflictError):
            await UserRepository(db_session).delete(user_id)

        remaining = await _count(db_session, User, User.id == user_id)
        assert remaining == 1

    async def test_delete_content_free_user_succeeds(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        await db_session.commit()

        deleted = await UserRepository(db_session).delete(user.id)
        assert deleted == 1


class TestDeviceCascadeDelete:
    async def test_delete_device_cascades_to_all_children(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        device = await create_device(db_session, "SN-CASCADE")
        profile = await create_profile(db_session, created_by=user.id)
        app = await create_mobile_app(db_session, created_by=user.id)
        group = await create_static_group(db_session, created_by=user.id)
        attr = await create_extension_attribute(db_session, created_by=user.id)

        await add_command(db_session, device_id=device.id, created_by=user.id)
        await add_profile_assignment(db_session, profile_id=profile.id, device_id=device.id)
        await add_mobile_app_assignment(db_session, mobile_app_id=app.id, device_id=device.id)
        await add_static_group_device(db_session, group.id, device.serial_number)
        await add_extension_attribute_value(
            db_session,
            device_id=device.id,
            extension_attribute_id=attr.id,
            extension_attribute_name=attr.name,
        )
        await db_session.commit()

        deleted = await DeviceRepository(db_session).delete(device.id)
        assert deleted == 1

        assert await _count(db_session, Command, Command.device_id == device.id) == 0
        assert await _count(db_session, ProfileAssignment, ProfileAssignment.device_id == device.id) == 0
        assert await _count(db_session, MobileAppAssignment, MobileAppAssignment.device_id == device.id) == 0
        assert (
            await _count(
                db_session,
                StaticGroupDevice,
                StaticGroupDevice.device_serial_number == device.serial_number,
            )
            == 0
        )
        assert (
            await _count(
                db_session,
                DeviceExtensionAttributeValue,
                DeviceExtensionAttributeValue.device_id == device.id,
            )
            == 0
        )


class TestProfileCascadeDelete:
    async def test_delete_profile_cascades_assignments(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        device = await create_device(db_session, "SN-PROFILE")
        profile = await create_profile(db_session, created_by=user.id)
        await add_profile_assignment(db_session, profile_id=profile.id, device_id=device.id)
        await db_session.commit()

        deleted = await ProfileRepository(db_session).delete(profile.id)
        assert deleted == 1
        assert await _count(db_session, ProfileAssignment, ProfileAssignment.profile_id == profile.id) == 0


class TestMobileAppCascadeDelete:
    async def test_delete_mobile_app_cascades_assignments(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        device = await create_device(db_session, "SN-MOBILE")
        app = await create_mobile_app(db_session, created_by=user.id)
        await add_mobile_app_assignment(db_session, mobile_app_id=app.id, device_id=device.id)
        await db_session.commit()

        deleted = await MobileAppRepository(db_session).delete(app.id)
        assert deleted == 1
        assert await _count(db_session, MobileAppAssignment, MobileAppAssignment.mobile_app_id == app.id) == 0


class TestExtensionAttributeCascadeDelete:
    async def test_delete_attribute_cascades_values(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        device = await create_device(db_session, "SN-EA")
        attr = await create_extension_attribute(db_session, created_by=user.id)
        await add_extension_attribute_value(
            db_session,
            device_id=device.id,
            extension_attribute_id=attr.id,
            extension_attribute_name=attr.name,
        )
        await db_session.commit()

        deleted = await ExtensionAttributeRepository(db_session).delete(attr.id)
        assert deleted == 1
        assert await _count(db_session, ExtensionAttribute, ExtensionAttribute.id == attr.id) == 0
        assert (
            await _count(
                db_session,
                DeviceExtensionAttributeValue,
                DeviceExtensionAttributeValue.extension_attribute_id == attr.id,
            )
            == 0
        )


class TestDanglingForeignKeyRejected:
    async def test_insert_command_with_missing_device_rejected(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session)
        db_session.add(
            Command(
                device_id=999999,
                command_type="LOCK",
                status="PENDING",
                created_by=user.id,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_insert_command_with_missing_creator_rejected(self, db_session: AsyncSession) -> None:
        device = await create_device(db_session, "SN-ORPHAN")
        db_session.add(
            Command(
                device_id=device.id,
                command_type="LOCK",
                status="PENDING",
                created_by=999999,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async def test_insert_static_group_membership_with_missing_group_rejected(self, db_session: AsyncSession) -> None:
        device = await create_device(db_session, "SN-ORPHAN-GROUP")
        db_session.add(
            StaticGroupDevice(
                static_group_id=999999,
                device_serial_number=device.serial_number,
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.flush()
