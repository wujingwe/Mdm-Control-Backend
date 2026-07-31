from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.devices import router as devices_router
from app.api.v1.extension_attributes import router as extension_attributes_router
from app.api.v1.inventory_search import router as inventory_search_router
from app.api.v1.mobile_apps import router as mobile_apps_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.smart_groups import router as smart_groups_router
from app.api.v1.static_groups import router as static_groups_router
from app.api.v1.users import router as users_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(devices_router)
router.include_router(profiles_router)
router.include_router(smart_groups_router)
router.include_router(static_groups_router)
router.include_router(users_router)
router.include_router(inventory_search_router)
router.include_router(extension_attributes_router)
router.include_router(mobile_apps_router)
