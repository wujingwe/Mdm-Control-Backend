from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.repositories.device import DeviceRepository
from app.repositories.inventory_search import InventorySearchRepository
from app.repositories.policy import PolicyRepository
from app.repositories.smart_group import SmartGroupRepository
from app.repositories.static_group import StaticGroupRepository
from app.services.device import DeviceService
from app.services.inventory_search import InventorySearchService
from app.services.policy import PolicyService
from app.services.smart_group import SmartGroupService
from app.services.static_group import StaticGroupService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


def get_device_service(db: AsyncSession = Depends(get_db)) -> DeviceService:
    return DeviceService(DeviceRepository(db))


def get_policy_service(db: AsyncSession = Depends(get_db)) -> PolicyService:
    return PolicyService(PolicyRepository(db))


def get_smart_group_service(db: AsyncSession = Depends(get_db)) -> SmartGroupService:
    return SmartGroupService(SmartGroupRepository(db))


def get_static_group_service(db: AsyncSession = Depends(get_db)) -> StaticGroupService:
    return StaticGroupService(StaticGroupRepository(db))


def get_inventory_search_service(db: AsyncSession = Depends(get_db)) -> InventorySearchService:
    return InventorySearchService(InventorySearchRepository(db))
