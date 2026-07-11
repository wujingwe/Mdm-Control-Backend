import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_group_service
from app.schemas.common import Message, PaginatedResponse
from app.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    SmartGroupCreate,
    SmartGroupResponse,
    SmartGroupUpdate,
)
from app.services.group import GroupService
from app.notification.sse import notify_group_policy_assignment
from app.webhook_client import revalidate

logger = logging.getLogger(__name__)


smart_groups_router = APIRouter(prefix="/smart-groups", tags=["Smart Groups"])
static_groups_router = APIRouter(prefix="/static-groups", tags=["Static Groups"])


@smart_groups_router.get("", response_model=PaginatedResponse[SmartGroupResponse])
async def list_smart_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: GroupService = Depends(get_group_service),
) -> PaginatedResponse[SmartGroupResponse]:
    items = await service.list_groups(skip=skip, limit=limit, is_smart=True)
    total = await service.repo.count(is_smart=True)
    return PaginatedResponse(
        items=[SmartGroupResponse.model_validate(g) for g in items],
        total=total, skip=skip, limit=limit,
    )


@static_groups_router.get("", response_model=PaginatedResponse[GroupResponse])
async def list_static_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: GroupService = Depends(get_group_service),
) -> PaginatedResponse[GroupResponse]:
    items = await service.list_groups(skip=skip, limit=limit, is_smart=False)
    total = await service.repo.count(is_smart=False)
    return PaginatedResponse(
        items=[GroupResponse.model_validate(g) for g in items],
        total=total, skip=skip, limit=limit,
    )


@smart_groups_router.get("/{group_id}", response_model=SmartGroupResponse)
async def get_smart_group(
    group_id: int,
    service: GroupService = Depends(get_group_service),
) -> SmartGroupResponse:
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return SmartGroupResponse.model_validate(group)


@static_groups_router.get("/{group_id}", response_model=GroupResponse)
async def get_static_group(
    group_id: int,
    service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupResponse.model_validate(group)


@smart_groups_router.post("", response_model=SmartGroupResponse, status_code=201)
async def create_smart_group(
    data: SmartGroupCreate,
    service: GroupService = Depends(get_group_service),
) -> SmartGroupResponse:
    criteria_dicts = [c.model_dump() for c in data.criteria]
    group = await service.create_group({
        "name": data.name,
        "description": data.description,
        "criteria": criteria_dicts,
        "is_smart": True,
        "created_by": data.created_by,
    })
    await revalidate(["groups"])
    return SmartGroupResponse.model_validate(group)


@static_groups_router.post("", response_model=GroupResponse, status_code=201)
async def create_static_group(
    data: GroupCreate,
    service: GroupService = Depends(get_group_service),
) -> GroupResponse:
    payload = data.model_dump()
    payload["is_smart"] = False
    group = await service.create_group(payload)
    await revalidate(["groups"])
    return GroupResponse.model_validate(group)


@smart_groups_router.put("/{group_id}", response_model=SmartGroupResponse)
async def update_smart_group(
    group_id: int,
    data: SmartGroupUpdate,
    service: GroupService = Depends(get_group_service),
) -> SmartGroupResponse:
    existing = await service.get_group(group_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Group not found")
    update: dict = {}
    if data.name is not None:
        update["name"] = data.name
    if data.description is not None:
        update["description"] = data.description
    if data.criteria is not None:
        update["criteria"] = [c.model_dump() for c in data.criteria]
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = await service.update_group(group_id, update)
    await revalidate(["groups"])
    return SmartGroupResponse.model_validate(updated)


@static_groups_router.put("/{group_id}", response_model=GroupResponse)
async def update_static_group(
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


@smart_groups_router.delete("/{group_id}", response_model=Message)
async def delete_smart_group(
    group_id: int,
    service: GroupService = Depends(get_group_service),
) -> Message:
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    await revalidate(["groups"])
    return Message(detail="Group deleted")


@static_groups_router.delete("/{group_id}", response_model=Message)
async def delete_static_group(
    group_id: int,
    service: GroupService = Depends(get_group_service),
) -> Message:
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    await revalidate(["groups"])
    return Message(detail="Group deleted")


@smart_groups_router.post("/{group_id}/policies", response_model=SmartGroupResponse, status_code=201)
async def assign_policy_to_smart_group(
    group_id: int,
    policy_id: int = Query(...),
    service: GroupService = Depends(get_group_service),
) -> SmartGroupResponse:
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
    return SmartGroupResponse.model_validate(group)


@static_groups_router.post("/{group_id}/policies", response_model=GroupResponse, status_code=201)
async def assign_policy_to_static_group(
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
