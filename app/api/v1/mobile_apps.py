from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.common.schemas import PaginatedResponse
from app.dependencies import get_mobile_app_service, require_permission
from app.mobile_apps.schemas import (
    MobileAppCreate,
    MobileAppResponse,
    MobileAppUpdate,
)
from app.mobile_apps.services import MobileAppService
from app.users.models import User
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
    current_user: User = Depends(require_permission("editor")),
) -> MobileAppResponse:
    app = await service.create_mobile_app(data, current_user.id)
    await revalidate(["mobile-apps"])
    return MobileAppResponse.model_validate(app)


@router.put("/{mobile_app_id}", response_model=MobileAppResponse)
async def update_mobile_app(
    mobile_app_id: int,
    data: MobileAppUpdate,
    service: MobileAppService = Depends(get_mobile_app_service),
    _current_user: User = Depends(require_permission("editor")),
) -> MobileAppResponse:
    updated = await service.update_mobile_app(mobile_app_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile app not found")
    await revalidate(["mobile-apps"])
    return MobileAppResponse.model_validate(updated)


@router.delete("/{mobile_app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mobile_app(
    mobile_app_id: int,
    service: MobileAppService = Depends(get_mobile_app_service),
    _current_user: User = Depends(require_permission("editor")),
) -> None:
    deleted = await service.delete_mobile_app(mobile_app_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile app not found")
    await revalidate(["mobile-apps"])
