import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_smart_group_service
from app.schemas.common import Message, PaginatedResponse
from app.schemas.group import SmartGroupCreate, SmartGroupResponse, SmartGroupUpdate
from app.services.smart_group import SmartGroupService
from app.notification.sse import notify_group_policy_assignment
from app.webhook_client import revalidate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/smart-groups", tags=["Smart Groups"])


@router.get("", response_model=PaginatedResponse[SmartGroupResponse])
async def list_smart_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SmartGroupService = Depends(get_smart_group_service),
) -> PaginatedResponse[SmartGroupResponse]:
    items = await service.list_groups(skip=skip, limit=limit)
    total = await service.repo.count()
    return PaginatedResponse(
        items=[SmartGroupResponse.model_validate(g) for g in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{group_id}", response_model=SmartGroupResponse)
async def get_smart_group(
    group_id: int,
    service: SmartGroupService = Depends(get_smart_group_service),
) -> SmartGroupResponse:
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Smart group not found")
    return SmartGroupResponse.model_validate(group)


@router.post("", response_model=SmartGroupResponse, status_code=201)
async def create_smart_group(
    data: SmartGroupCreate,
    service: SmartGroupService = Depends(get_smart_group_service),
) -> SmartGroupResponse:
    criteria_dicts = [c.model_dump() for c in data.criteria]
    group = await service.create_group({
        "name": data.name,
        "description": data.description,
        "criteria": criteria_dicts,
        "created_by": data.created_by,
    })
    await revalidate(["smart-groups"])
    return SmartGroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=SmartGroupResponse)
async def update_smart_group(
    group_id: int,
    data: SmartGroupUpdate,
    service: SmartGroupService = Depends(get_smart_group_service),
) -> SmartGroupResponse:
    existing = await service.get_group(group_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Smart group not found")
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
    await revalidate(["smart-groups"])
    return SmartGroupResponse.model_validate(updated)


@router.delete("/{group_id}", response_model=Message)
async def delete_smart_group(
    group_id: int,
    service: SmartGroupService = Depends(get_smart_group_service),
) -> Message:
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Smart group not found")
    await revalidate(["smart-groups"])
    return Message(detail="Smart group deleted")


@router.post("/{group_id}/policies", response_model=SmartGroupResponse, status_code=201)
async def assign_policy_to_smart_group(
    group_id: int,
    policy_id: int = Query(...),
    service: SmartGroupService = Depends(get_smart_group_service),
) -> SmartGroupResponse:
    group = await service.assign_policy(group_id, policy_id)
    if not group:
        raise HTTPException(status_code=404, detail="Smart group or policy not found")
    try:
        await notify_group_policy_assignment(
            group_id=group.id,
            group_name=group.name,
            policy_id=policy_id,
            policy_name=next((p.name for p in group.policies if p.id == policy_id), ""),
        )
    except Exception as e:
        logger.error(f"SSE notification failed, continuing: {e}", exc_info=True)
    await revalidate(["smart-groups", "policies"])
    return SmartGroupResponse.model_validate(group)
