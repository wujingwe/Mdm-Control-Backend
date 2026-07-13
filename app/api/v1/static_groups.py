from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_static_group_service
from app.common.schemas import PaginatedResponse
from app.static_groups.schemas import StaticGroupCreate, StaticGroupResponse, StaticGroupUpdate
from app.static_groups.services import StaticGroupService
from app.webhook_client import revalidate

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
    group = await service.create_group(data)
    await revalidate(["static-groups"])
    resp = StaticGroupResponse.model_validate(group)
    resp.device_serial_numbers = data.device_serial_numbers or []
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
    updated = await service.update_group(group_id, data)
    if data.device_serial_numbers is not None:
        await service.set_device_serial_numbers(group_id, data.device_serial_numbers)
    await revalidate(["static-groups"])
    serials = await service.get_device_serial_numbers(group_id)
    resp = StaticGroupResponse.model_validate(updated)
    resp.device_serial_numbers = serials
    return resp


@router.delete("/{group_id}")
async def delete_static_group(
    group_id: int,
    service: StaticGroupService = Depends(get_static_group_service),
) -> dict:
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Static group not found")
    await revalidate(["static-groups"])
    return {"detail": "Static group deleted"}
