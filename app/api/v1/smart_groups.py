from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_smart_group_service
from app.common.schemas import Message, PaginatedResponse
from app.smart_groups.schemas import (
    SmartGroupCreate,
    SmartGroupResponse,
    SmartGroupUpdate,
)
from app.smart_groups.services import SmartGroupService
from app.webhook_client import revalidate

router = APIRouter(prefix="/smart-groups", tags=["Smart Groups"])


@router.get("", response_model=PaginatedResponse[SmartGroupResponse])
async def list_smart_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SmartGroupService = Depends(get_smart_group_service),
) -> PaginatedResponse[SmartGroupResponse]:
    items, total = await service.list_groups(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[SmartGroupResponse.model_validate(g) for g in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{group_id}", response_model=SmartGroupResponse)
async def get_smart_group(
    group_id: int,
    service: SmartGroupService = Depends(get_smart_group_service),
) -> SmartGroupResponse:
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Smart group not found"
        )
    return SmartGroupResponse.model_validate(group)


@router.post("", response_model=SmartGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_smart_group(
    data: SmartGroupCreate,
    service: SmartGroupService = Depends(get_smart_group_service),
) -> SmartGroupResponse:
    group = await service.create_group(data)
    await revalidate(["smart-groups"])
    return SmartGroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=SmartGroupResponse)
async def update_smart_group(
    group_id: int,
    data: SmartGroupUpdate,
    service: SmartGroupService = Depends(get_smart_group_service),
) -> SmartGroupResponse:
    updated = await service.update_group(group_id, data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Smart group not found"
        )
    await revalidate(["smart-groups"])
    return SmartGroupResponse.model_validate(updated)


@router.delete("/{group_id}", response_model=Message)
async def delete_smart_group(
    group_id: int,
    service: SmartGroupService = Depends(get_smart_group_service),
) -> Message:
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Smart group not found"
        )
    await revalidate(["smart-groups"])
    return Message(detail="Smart group deleted")
