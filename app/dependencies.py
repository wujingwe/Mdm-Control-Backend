from collections.abc import AsyncGenerator
from typing import Callable, Awaitable

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands.repositories import CommandRepository
from app.commands.services import CommandService
from app.core.security import verify_token
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
from app.profiles.reconciler import ProfileAssignmentReconciler
from app.profiles.services import ProfileService
from app.smart_groups.repositories import SmartGroupRepository
from app.smart_groups.services import SmartGroupService
from app.static_groups.repositories import StaticGroupRepository
from app.static_groups.services import StaticGroupService
from app.users.models import User
from app.users.repositories import UserRepository
from app.users.services import UserService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


async def get_current_user(
    token: dict = Depends(verify_token),
    user_service: UserService = Depends(get_user_service),
) -> User:
    user = await user_service.get_user_by_email(token["email"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_permission(
    permission: str,
) -> Callable[..., Awaitable[User]]:
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if "admin" not in current_user.permissions and permission not in current_user.permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return _check


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


def get_reconciler(db: AsyncSession = Depends(get_db)) -> ProfileAssignmentReconciler:
    from app.messaging.producer import rabbitmq_producer

    return ProfileAssignmentReconciler(ProfileRepository(db), rabbitmq_producer)


def get_command_service(db: AsyncSession = Depends(get_db)) -> CommandService:
    return CommandService(CommandRepository(db))
