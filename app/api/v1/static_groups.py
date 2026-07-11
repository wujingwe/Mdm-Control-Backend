import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_static_group_service
from app.schemas.common import Message, PaginatedResponse
from app.schemas.group import StaticGroupCreate, StaticGroupResponse, StaticGroupUpdate
from app.services.static_group import StaticGroupService
from app.notification.sse import notify_group_policy_assignment
from app.webhook_client import revalidate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/static-groups", tags=["Static Groups"])


@router.get("", response_model=PaginatedResponse[StaticGroupResponse])
async def list_static_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: StaticGroupService = Depends(get_static_group_service),
) -> PaginatedResponse[StaticGroupResponse]:
    items = await service.list_groups(skip=skip, limit=limit)
    total = await service.repo.count()
    result = []
    for g in items:
        serials = await service.get_device_serial_numbers(g.id)
        resp = StaticGroupResponse.model_validate(g)
        resp.device_serial_numbers = serials
        result.append(resp)
    return PaginatedResponse(items=result, total=total, skip=skip, limit=limit)


@router.get("/{group_id}", response_model=StaticGroupResponse)
async def get_static_group(
    group_id: int,
    service: StaticGroupService = Depends(get_static_group_service),
) -> StaticGroupResponse:
    group = await service.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Static group not found")
    serials = await service.get_device_serial_numbers(group.id)
    resp = StaticGroupResponse.model_validate(group)
    resp.device_serial_numbers = serials
    return resp


@router.post("", response_model=StaticGroupResponse, status_code=201)
async def create_static_group(
    data: StaticGroupCreate,
    service: StaticGroupService = Depends(get_static_group_service),
) -> StaticGroupResponse:
    group = await service.create_group({
        "name": data.name,
        "description": data.description,
        "created_by": data.created_by,
    })
    if data.device_serial_numbers:
        await service.set_device_serial_numbers(group.id, data.device_serial_numbers)
    await revalidate(["static-groups"])
    resp = StaticGroupResponse.model_validate(group)
    resp.device_serial_numbers = data.device_serial_numbers
    return resp


@router.put("/{group_id}", response_model=StaticGroupResponse)
async def update_static_group(
    group_id: int,
    data: StaticGroupUpdate,
    service: StaticGroupService = Depends(get_static_group_service),
) -> StaticGroupResponse:
    existing = await service.get_group(group_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Static group not found")
    update: dict = {}
    if data.name is not None:
        update["name"] = data.name
    if data.description is not None:
        update["description"] = data.description
    if not update and data.device_serial_numbers is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    if update:
        updated = await service.update_group(group_id, update)
    else:
        updated = existing
    if data.device_serial_numbers is not None:
        await service.set_device_serial_numbers(group_id, data.device_serial_numbers)
    await revalidate(["static-groups"])
    serials = await service.get_device_serial_numbers(group_id)
    resp = StaticGroupResponse.model_validate(updated)
    resp.device_serial_numbers = serials
    return resp


@router.delete("/{group_id}", response_model=Message)
async def delete_static_group(
    group_id: int,
    service: StaticGroupService = Depends(get_static_group_service),
) -> Message:
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Static group not found")
    await revalidate(["static-groups"])
    return Message(detail="Static group deleted")


@router.post("/{group_id}/policies", response_model=StaticGroupResponse, status_code=201)
async def assign_policy_to_static_group(
    group_id: int,
    policy_id: int = Query(...),
    service: StaticGroupService = Depends(get_static_group_service),
) -> StaticGroupResponse:
    group = await service.assign_policy(group_id, policy_id)
    if not group:
        raise HTTPException(status_code=404, detail="Static group or policy not found")
    try:
        await notify_group_policy_assignment(
            group_id=group.id,
            group_name=group.name,
            policy_id=policy_id,
            policy_name=next((p.name for p in group.policies if p.id == policy_id), ""),
        )
    except Exception as e:
        logger.error(f"SSE notification failed, continuing: {e}", exc_info=True)
    await revalidate(["static-groups", "policies"])
    serials = await service.get_device_serial_numbers(group_id)
    resp = StaticGroupResponse.model_validate(group)
    resp.device_serial_numbers = serials
    return resp
