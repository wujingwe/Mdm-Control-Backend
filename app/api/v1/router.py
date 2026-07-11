from fastapi import APIRouter
from app.api.v1.devices import router as devices_router
from app.api.v1.policies import router as policies_router
from app.api.v1.groups import smart_groups_router, static_groups_router
from app.api.v1.users import router as users_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.inventory_search import router as inventory_search_router

router = APIRouter(prefix="/v1")
router.include_router(devices_router)
router.include_router(policies_router)
router.include_router(smart_groups_router)
router.include_router(static_groups_router)
router.include_router(users_router)
router.include_router(metrics_router)
router.include_router(inventory_search_router)
