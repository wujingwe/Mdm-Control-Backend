from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands.repositories import CommandRepository
from app.commands.services import CommandService
from app.database import async_session
from app.devices.repositories import DeviceRepository
from app.devices.services import DeviceService
from app.extension_attributes.repositories import ExtensionAttributeRepository
from app.extension_attributes.services import ExtensionAttributeService
from app.inventory_search.repositories import InventorySearchRepository
from app.inventory_search.services import InventorySearchService
from app.mobile_apps.repositories import MobileAppRepository
from app.mobile_apps.services import MobileAppService
from app.profiles.repositories import ProfileRepository
from app.profiles.services import ProfileService
from app.smart_groups.repositories import SmartGroupRepository
from app.smart_groups.services import SmartGroupService
from app.static_groups.repositories import StaticGroupRepository
from app.static_groups.services import StaticGroupService
from app.users.repositories import UserRepository
from app.users.services import UserService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_device_service(db: AsyncSession = Depends(get_db)) -> DeviceService:
    return DeviceService(DeviceRepository(db))


def get_smart_group_service(db: AsyncSession = Depends(get_db)) -> SmartGroupService:
    return SmartGroupService(SmartGroupRepository(db))


def get_static_group_service(db: AsyncSession = Depends(get_db)) -> StaticGroupService:
    return StaticGroupService(StaticGroupRepository(db))


def get_inventory_search_service(
    db: AsyncSession = Depends(get_db),
) -> InventorySearchService:
    return InventorySearchService(InventorySearchRepository(db))


def get_mobile_app_service(db: AsyncSession = Depends(get_db)) -> MobileAppService:
    return MobileAppService(MobileAppRepository(db))


def get_extension_attribute_service(
    db: AsyncSession = Depends(get_db),
) -> ExtensionAttributeService:
    return ExtensionAttributeService(ExtensionAttributeRepository(db))


def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    return ProfileService(ProfileRepository(db))


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


def get_command_service(db: AsyncSession = Depends(get_db)) -> CommandService:
    return CommandService(CommandRepository(db))
