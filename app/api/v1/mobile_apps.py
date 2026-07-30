from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.infra.common.schemas import PaginatedResponse
from app.dependencies import get_mobile_app_service, get_reconciler, require_permission
from app.infra.reconciler.reconciler import AssignmentReconciler
from app.domains.mobile_apps.schemas import (
    MobileAppAssignmentResponse,
    MobileAppCreate,
    MobileAppResponse,
    MobileAppStatusUpdate,
    MobileAppUpdate,
)
from app.domains.mobile_apps.services import MobileAppService
from app.domains.users.models import User
from app.webhook_client import revalidate

router = APIRouter(prefix="/mobile-apps", tags=["MobileApps"])


@router.get("", response_model=PaginatedResponse[MobileAppResponse])
async def list_mobile_apps(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: MobileAppService = Depends(get_mobile_app_service),
) -> PaginatedResponse[MobileAppResponse]:
    items, total = await service.list_mobile_apps(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[MobileAppResponse.model_validate(app) for app in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{mobile_app_id}", response_model=MobileAppResponse)
async def get_mobile_app(
    mobile_app_id: int,
    service: MobileAppService = Depends(get_mobile_app_service),
) -> MobileAppResponse:
    app = await service.get_mobile_app(mobile_app_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile app not found")
    return MobileAppResponse.model_validate(app)


@router.post("", response_model=MobileAppResponse, status_code=status.HTTP_201_CREATED)
async def create_mobile_app(
    data: MobileAppCreate,
    service: MobileAppService = Depends(get_mobile_app_service),
    reconciler: AssignmentReconciler = Depends(get_reconciler),
    current_user: User = Depends(require_permission("editor")),
) -> MobileAppResponse:
    app = await service.create_mobile_app(data, current_user.id)
    if data.scope.targets:
        await reconciler.request_recalculate_mobile_app(app.id)
    await revalidate(["mobile-apps"])
    return MobileAppResponse.model_validate(app)


@router.put("/{mobile_app_id}", response_model=MobileAppResponse)
async def update_mobile_app(
    mobile_app_id: int,
    data: MobileAppUpdate,
    service: MobileAppService = Depends(get_mobile_app_service),
    reconciler: AssignmentReconciler = Depends(get_reconciler),
    _current_user: User = Depends(require_permission("editor")),
) -> MobileAppResponse:
    updated = await service.update_mobile_app(mobile_app_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile app not found")
    if data.scope is not None:
        await reconciler.request_recalculate_mobile_app(mobile_app_id)
    await revalidate(["mobile-apps"])
    return MobileAppResponse.model_validate(updated)


@router.delete("/{mobile_app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mobile_app(
    mobile_app_id: int,
    service: MobileAppService = Depends(get_mobile_app_service),
    reconciler: AssignmentReconciler = Depends(get_reconciler),
    _current_user: User = Depends(require_permission("editor")),
) -> None:
    app = await service.get_mobile_app(mobile_app_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile app not found")
    for target in app.scope.targets:
        if target.scope_type == "SMART_GROUP" and target.target_id:
            await reconciler.recalculate_mobile_apps_for_smart_group(target.target_id)
        elif target.scope_type == "STATIC_GROUP" and target.target_id:
            await reconciler.recalculate_mobile_apps_for_static_group(target.target_id)
    await service.delete_mobile_app(mobile_app_id)
    await revalidate(["mobile-apps"])


@router.get("/{mobile_app_id}/assignments", response_model=list[MobileAppAssignmentResponse])
async def list_mobile_app_assignments(
    mobile_app_id: int,
    service: MobileAppService = Depends(get_mobile_app_service),
) -> list[MobileAppAssignmentResponse]:
    assignments = await service.get_assignments(mobile_app_id)
    return [MobileAppAssignmentResponse.model_validate(a) for a in assignments]


@router.put("/{mobile_app_id}/assignments/{device_id}/status", response_model=MobileAppAssignmentResponse)
async def update_mobile_app_assignment_status(
    mobile_app_id: int,
    device_id: int,
    data: MobileAppStatusUpdate,
    service: MobileAppService = Depends(get_mobile_app_service),
) -> MobileAppAssignmentResponse:
    assignment = await service.update_assignment_status(mobile_app_id, device_id, data.status.value)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    await revalidate(["mobile-apps"])
    return MobileAppAssignmentResponse.model_validate(assignment)
