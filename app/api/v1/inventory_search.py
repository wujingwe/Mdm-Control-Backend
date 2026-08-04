from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.infra.common.schemas import PaginatedResponse
from app.dependencies import get_inventory_search_service, require_permission
from app.domains.devices.schemas import DeviceResponse
from app.domains.inventory_search.schemas import (
    InventorySearchCreate,
    InventorySearchExecuteRequest,
    InventorySearchResponse,
    InventorySearchUpdate,
)
from app.domains.inventory_search.services import InventorySearchService
from app.domains.users.models import User
from app.webhook_client import revalidate

router = APIRouter(prefix="/inventory-search", tags=["InventorySearch"])


@router.get("", response_model=PaginatedResponse[InventorySearchResponse])
async def list_inventory_searches(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: InventorySearchService = Depends(get_inventory_search_service),
) -> PaginatedResponse[InventorySearchResponse]:
    items, total = await service.list_searches(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[InventorySearchResponse.model_validate(s) for s in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{search_id}", response_model=InventorySearchResponse)
async def get_inventory_search(
    search_id: int,
    service: InventorySearchService = Depends(get_inventory_search_service),
) -> InventorySearchResponse:
    search = await service.get_search(search_id)
    if not search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory search not found")
    return InventorySearchResponse.model_validate(search)


@router.post("", response_model=InventorySearchResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory_search(
    data: InventorySearchCreate,
    service: InventorySearchService = Depends(get_inventory_search_service),
    current_user: User = Depends(require_permission("editor")),
) -> InventorySearchResponse:
    search = await service.create_search(data, current_user.id)
    await revalidate(["inventory-search"])
    return InventorySearchResponse.model_validate(search)


@router.put("/{search_id}", response_model=InventorySearchResponse)
async def update_inventory_search(
    search_id: int,
    data: InventorySearchUpdate,
    service: InventorySearchService = Depends(get_inventory_search_service),
    _current_user: User = Depends(require_permission("editor")),
) -> InventorySearchResponse:
    if not data.model_fields_set:
        search = await service.get_search(search_id)
        if search is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory search not found")
        return InventorySearchResponse.model_validate(search)
    updated = await service.update_search(search_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory search not found")
    await revalidate(["inventory-search"])
    search = await service.get_search(search_id)
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory search not found")
    return InventorySearchResponse.model_validate(search)


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_search(
    search_id: int,
    service: InventorySearchService = Depends(get_inventory_search_service),
    _current_user: User = Depends(require_permission("admin")),
) -> None:
    deleted = await service.delete_search(search_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory search not found")
    await revalidate(["inventory-search"])


@router.post("/execute", response_model=list[DeviceResponse])
async def execute_inventory_search(
    data: InventorySearchExecuteRequest,
    service: InventorySearchService = Depends(get_inventory_search_service),
) -> list[DeviceResponse]:
    devices = await service.execute_search(data)
    return [DeviceResponse.model_validate(d) for d in devices]
