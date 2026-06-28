import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_group_service
from app.schemas.common import Message, PaginatedResponse
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse
from app.services.group import GroupService
from app.notification.sse import notify_group_policy_assignment
from app.webhook_client import revalidate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("", response_model=PaginatedResponse[GroupResponse])
async def list_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: GroupService = Depends(get_group_service),
) -> PaginatedResponse[GroupResponse]:
    items = await service.list_groups(skip=skip, limit=limit)
    total = await service.repo.count()
    return PaginatedResponse(
        items=[GroupResponse.model_validate(g) for g in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: int,
    service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupResponse.model_validate(group)


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    data: GroupCreate,
    service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    group = await service.create_group(data.model_dump())
    await revalidate(["groups"])
    return GroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    data: GroupUpdate,
    service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    group = await service.update_group(group_id, update_data)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await revalidate(["groups"])
    return GroupResponse.model_validate(group)


@router.delete("/{group_id}", response_model=Message)
async def delete_group(
    group_id: int,
    service: GroupService = Depends(get_group_service),
) -> Message:
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    await revalidate(["groups"])
    return Message(detail="Group deleted")


@router.post("/{group_id}/policies", response_model=GroupResponse, status_code=201)
async def assign_policy_to_group(
    group_id: int,
    policy_id: int = Query(...),
    service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    group = await service.assign_policy(group_id, policy_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group or policy not found")
    try:
        await notify_group_policy_assignment(
            group_id=group.id,
            group_name=group.name,
            policy_id=policy_id,
            policy_name=next((p.name for p in group.policies if p.id == policy_id), ""),
        )
    except Exception as e:
        logger.error(f"SSE notification failed, continuing: {e}", exc_info=True)
    await revalidate(["groups", "policies"])
    return GroupResponse.model_validate(group)
