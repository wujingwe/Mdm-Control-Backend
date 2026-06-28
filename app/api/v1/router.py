from fastapi import APIRouter
from app.api.v1.devices import router as devices_router
from app.api.v1.policies import router as policies_router
from app.api.v1.groups import router as groups_router
from app.api.v1.users import router as users_router
from app.api.v1.metrics import router as metrics_router

router = APIRouter(prefix="/v1")
router.include_router(devices_router)
router.include_router(policies_router)
router.include_router(groups_router)
router.include_router(users_router)
router.include_router(metrics_router)
