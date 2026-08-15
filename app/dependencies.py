import logging
from collections.abc import AsyncGenerator
from typing import Callable, Awaitable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.commands.repositories import CommandRepository
from app.domains.commands.services import CommandService
from app.infra.config.settings import settings
from app.infra.core.security import TokenClaims, verify_token
from app.infra.core.database import async_session
from app.domains.devices.repositories import DeviceRepository
from app.domains.devices.services import DeviceService
from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
from app.domains.extension_attributes.services import ExtensionAttributeService
from app.domains.inventory_search.repositories import InventorySearchRepository
from app.domains.inventory_search.services import InventorySearchService
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.mobile_apps.services import MobileAppService
from app.domains.profiles.repositories import ProfileRepository
from app.domains.profiles.services import ProfileService
from app.domains.shared.reconciliation_service import ReconciliationService
from app.domains.shared.sweep_service import SweepService
from app.domains.smart_groups.repositories import SmartGroupRepository
from app.domains.smart_groups.services import SmartGroupService
from app.domains.static_groups.repositories import StaticGroupRepository
from app.domains.static_groups.services import StaticGroupService
from app.domains.users.models import User
from app.domains.users.repositories import UserRepository
from app.domains.users.services import UserService
from app.infra.messaging.producer import rabbitmq_producer
from app.infra.reconciler.reconciler import AssignmentReconciler

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


async def get_current_user(
    token: TokenClaims = Depends(verify_token),
    user_service: UserService = Depends(get_user_service),
) -> User:
    user = await user_service.get_user_by_email(token.email)
    logger.info("Auth: get_current_user email=%r found=%s", token.email, user is not None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_permission(
    permission: str,
) -> Callable[[User], Awaitable[User]]:
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        allowed = "admin" in current_user.permissions or permission in current_user.permissions
        logger.info(
            "Auth: require_permission(%r) user=%r permissions=%r allowed=%s",
            permission,
            current_user.email,
            current_user.permissions,
            allowed,
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return _check


def require_sse_secret(x_sse_secret: str | None = Header(default=None, alias="X-SSE-SECRET")) -> None:
    if not settings.sse_secret:
        return
    if x_sse_secret != settings.sse_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid SSE secret")


def require_sweep_secret(x_sweep_secret: str | None = Header(default=None, alias="X-SWEEP-SECRET")) -> None:
    if not settings.sweep_secret:
        return
    if x_sweep_secret != settings.sweep_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sweep secret")


def get_assignment_reconciler(db: AsyncSession = Depends(get_db)) -> AssignmentReconciler:
    return AssignmentReconciler(
        ProfileRepository(db),
        MobileAppRepository(db),
        DeviceRepository(db),
        SmartGroupRepository(db),
        rabbitmq_producer,
    )


def get_sweep_service(
    reconciler: AssignmentReconciler = Depends(get_assignment_reconciler),
) -> SweepService:
    return SweepService(reconciler)


def get_reconciliation_service(db: AsyncSession = Depends(get_db)) -> ReconciliationService:
    return ReconciliationService(ProfileRepository(db), MobileAppRepository(db))


def get_device_service(
    db: AsyncSession = Depends(get_db),
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> DeviceService:
    return DeviceService(
        DeviceRepository(db),
        reconciliation_service,
        CommandRepository(db),
        ProfileRepository(db),
        MobileAppRepository(db),
    )


def get_smart_group_service(
    db: AsyncSession = Depends(get_db),
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> SmartGroupService:
    return SmartGroupService(
        SmartGroupRepository(db),
        ProfileRepository(db),
        MobileAppRepository(db),
        reconciliation_service,
    )


def get_static_group_service(
    db: AsyncSession = Depends(get_db),
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> StaticGroupService:
    return StaticGroupService(
        StaticGroupRepository(db),
        ProfileRepository(db),
        MobileAppRepository(db),
        reconciliation_service,
    )


def get_inventory_search_service(
    db: AsyncSession = Depends(get_db),
) -> InventorySearchService:
    return InventorySearchService(InventorySearchRepository(db))


def get_mobile_app_service(
    db: AsyncSession = Depends(get_db),
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> MobileAppService:
    return MobileAppService(MobileAppRepository(db), reconciliation_service)


def get_extension_attribute_service(
    db: AsyncSession = Depends(get_db),
) -> ExtensionAttributeService:
    return ExtensionAttributeService(ExtensionAttributeRepository(db))


def get_profile_service(
    db: AsyncSession = Depends(get_db),
    reconciliation_service: ReconciliationService = Depends(get_reconciliation_service),
) -> ProfileService:
    return ProfileService(ProfileRepository(db), reconciliation_service)


def get_command_service(db: AsyncSession = Depends(get_db)) -> CommandService:
    return CommandService(CommandRepository(db), DeviceRepository(db))
