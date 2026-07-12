from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_inventory_search_service
from app.common.schemas import Message, PaginatedResponse
from app.inventory_search.schemas import (
    InventorySearchCreate,
    InventorySearchResponse,
    InventorySearchUpdate,
)
from app.inventory_search.services import InventorySearchService
from app.webhook_client import revalidate

router = APIRouter(prefix="/inventory-search", tags=["Inventory Search"])


@router.get("", response_model=PaginatedResponse[InventorySearchResponse])
async def list_inventory_searches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: InventorySearchService = Depends(get_inventory_search_service),
) -> PaginatedResponse[InventorySearchResponse]:
    items, total = await service.list_searches(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[InventorySearchResponse.model_validate(s) for s in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{search_id}", response_model=InventorySearchResponse)
async def get_inventory_search(
    search_id: int,
    service: InventorySearchService = Depends(get_inventory_search_service),
) -> InventorySearchResponse:
    search = await service.get_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Inventory search not found")
    return InventorySearchResponse.model_validate(search)


@router.post("", response_model=InventorySearchResponse, status_code=201)
async def create_inventory_search(
    data: InventorySearchCreate,
    service: InventorySearchService = Depends(get_inventory_search_service),
) -> InventorySearchResponse:
    criteria_dicts = [c.model_dump() for c in data.criteria]
    search = await service.create_search({
        "name": data.name,
        "description": data.description,
        "criteria": criteria_dicts,
        "created_by": data.created_by,
    })
    await revalidate(["inventory-search"])
    return InventorySearchResponse.model_validate(search)


@router.put("/{search_id}", response_model=InventorySearchResponse)
async def update_inventory_search(
    search_id: int,
    data: InventorySearchUpdate,
    service: InventorySearchService = Depends(get_inventory_search_service),
) -> InventorySearchResponse:
    existing = await service.get_search(search_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Inventory search not found")
    update: dict = {}
    if data.name is not None:
        update["name"] = data.name
    if data.description is not None:
        update["description"] = data.description
    if data.criteria is not None:
        update["criteria"] = [c.model_dump() for c in data.criteria]
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    updated = await service.update_search(search_id, update)
    await revalidate(["inventory-search"])
    return InventorySearchResponse.model_validate(updated)


@router.delete("/{search_id}", response_model=Message)
async def delete_inventory_search(
    search_id: int,
    service: InventorySearchService = Depends(get_inventory_search_service),
) -> Message:
    deleted = await service.delete_search(search_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Inventory search not found")
    await revalidate(["inventory-search"])
    return Message(detail="Inventory search deleted")
