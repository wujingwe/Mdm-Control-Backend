from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.common.schemas import PaginatedResponse
from app.dependencies import get_reconciler, get_static_group_service, require_permission
from app.profiles.reconciler import ProfileAssignmentReconciler
from app.static_groups.schemas import (
    StaticGroupCreate,
    StaticGroupResponse,
    StaticGroupUpdate,
)
from app.static_groups.services import StaticGroupService
from app.users.models import User
from app.webhook_client import revalidate

router = APIRouter(prefix="/static-groups", tags=["Static Groups"])


@router.get("", response_model=PaginatedResponse[StaticGroupResponse])
async def list_static_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: StaticGroupService = Depends(get_static_group_service),
) -> PaginatedResponse[StaticGroupResponse]:
    items, total = await service.list_groups(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[StaticGroupResponse.model_validate(g) for g in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{group_id}", response_model=StaticGroupResponse)
async def get_static_group(
    group_id: int,
    service: StaticGroupService = Depends(get_static_group_service),
) -> StaticGroupResponse:
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Static group not found")
    resp = StaticGroupResponse.model_validate(group)
    return resp


@router.post("", response_model=StaticGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_static_group(
    data: StaticGroupCreate,
    service: StaticGroupService = Depends(get_static_group_service),
    reconciler: ProfileAssignmentReconciler = Depends(get_reconciler),
    current_user: User = Depends(require_permission("editor")),
) -> StaticGroupResponse:
    group = await service.create_group(data, current_user.id)
    if group:
        await reconciler.recalculate_profiles_for_static_group(group.id)
    await revalidate(["static-groups"])
    return StaticGroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=StaticGroupResponse)
async def update_static_group(
    group_id: int,
    data: StaticGroupUpdate,
    service: StaticGroupService = Depends(get_static_group_service),
    reconciler: ProfileAssignmentReconciler = Depends(get_reconciler),
    _current_user: User = Depends(require_permission("editor")),
) -> StaticGroupResponse:
    updated = await service.update_group(group_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Static group not found")
    await reconciler.recalculate_profiles_for_static_group(group_id)
    await revalidate(["static-groups"])
    return StaticGroupResponse.model_validate(updated)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_static_group(
    group_id: int,
    service: StaticGroupService = Depends(get_static_group_service),
    reconciler: ProfileAssignmentReconciler = Depends(get_reconciler),
    _current_user: User = Depends(require_permission("editor")),
) -> None:
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Static group not found")
    await reconciler.purge_static_group(group_id)
    await revalidate(["static-groups"])
