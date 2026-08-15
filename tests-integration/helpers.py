"""Factory helpers for MariaDB integration tests (tests-integration/)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.commands.enums import CommandStatus, CommandType
from app.domains.commands.models import Command
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.devices.models import Device, DeviceExtensionAttributeValue
from app.domains.extension_attributes.enums import ExtensionDataType, ExtensionInputType
from app.domains.extension_attributes.models import ExtensionAttribute
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.profiles.models import Profile, ProfileAssignment
from app.domains.profiles.schemas.policy import Policy
from app.domains.shared.scope import Scope, ScopeTarget, ScopeType
from app.domains.static_groups.models import StaticGroup, StaticGroupDevice
from app.domains.users.models import User


async def create_user(session: AsyncSession, email: str = "user@test.local", name: str = "Test User") -> User:
    user = User(email=email, name=name)
    session.add(user)
    await session.flush()
    return user


async def create_device(
    session: AsyncSession,
    serial_number: str = "SN-0001",
    status: DeviceStatus = DeviceStatus.ENROLLED,
    connection_status: ConnectionStatus = ConnectionStatus.CONNECTED,
) -> Device:
    device = Device(
        name=f"Device {serial_number}",
        serial_number=serial_number,
        os_version="Android 14",
        connection_status=connection_status,
        status=status,
    )
    session.add(device)
    await session.flush()
    return device


async def create_profile(session: AsyncSession, created_by: int, name: str = "Profile 1") -> Profile:
    profile = Profile(
        name=name,
        description="Integration test profile",
        policy=Policy(screenCaptureDisabled=True, addUserDisabled=True),
        scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        created_by=created_by,
    )
    session.add(profile)
    await session.flush()
    return profile


async def create_mobile_app(
    session: AsyncSession,
    created_by: int,
    package_name: str = "com.example.app",
) -> MobileApp:
    app = MobileApp(
        name="Example App",
        enabled=True,
        package_version="1.0.0",
        package_name=package_name,
        scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
        created_by=created_by,
    )
    session.add(app)
    await session.flush()
    return app


async def create_static_group(session: AsyncSession, created_by: int, name: str = "Static Group") -> StaticGroup:
    group = StaticGroup(name=name, description="Integration test group", created_by=created_by)
    session.add(group)
    await session.flush()
    return group


async def create_extension_attribute(
    session: AsyncSession,
    created_by: int,
    name: str = "Department",
) -> ExtensionAttribute:
    attr = ExtensionAttribute(
        name=name,
        description="Integration test attribute",
        data_type=ExtensionDataType.STRING,
        input_type=ExtensionInputType.TEXT_FIELD,
        created_by=created_by,
    )
    session.add(attr)
    await session.flush()
    return attr


async def add_command(
    session: AsyncSession,
    device_id: int,
    created_by: int,
    command_type: CommandType = CommandType.LOCK,
    status: CommandStatus = CommandStatus.PENDING,
) -> Command:
    command = Command(
        device_id=device_id,
        command_type=command_type,
        status=status,
        created_by=created_by,
    )
    session.add(command)
    await session.flush()
    return command


async def add_profile_assignment(
    session: AsyncSession,
    profile_id: int,
    device_id: int,
) -> ProfileAssignment:
    assignment = ProfileAssignment(
        profile_id=profile_id,
        device_id=device_id,
        status=AssignmentStatus.PENDING,
        desired_state=AssignmentDesiredState.PRESENT,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def add_mobile_app_assignment(
    session: AsyncSession,
    mobile_app_id: int,
    device_id: int,
) -> MobileAppAssignment:
    assignment = MobileAppAssignment(
        mobile_app_id=mobile_app_id,
        device_id=device_id,
        status=AssignmentStatus.PENDING,
        desired_state=AssignmentDesiredState.PRESENT,
    )
    session.add(assignment)
    await session.flush()
    return assignment


async def add_static_group_device(
    session: AsyncSession,
    static_group_id: int,
    device_serial_number: str,
) -> StaticGroupDevice:
    membership = StaticGroupDevice(
        static_group_id=static_group_id,
        device_serial_number=device_serial_number,
    )
    session.add(membership)
    await session.flush()
    return membership


async def add_extension_attribute_value(
    session: AsyncSession,
    device_id: int,
    extension_attribute_id: int,
    extension_attribute_name: str,
    value: str = "Engineering",
) -> DeviceExtensionAttributeValue:
    row = DeviceExtensionAttributeValue(
        device_id=device_id,
        extension_attribute_id=extension_attribute_id,
        extension_attribute_name=extension_attribute_name,
        value=value,
    )
    session.add(row)
    await session.flush()
    return row
