from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.common.schemas import PaginatedResponse
from app.dependencies import get_device_service
from app.devices.schemas import DeviceResponse
from app.devices.services import DeviceService

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
    service: DeviceService = Depends(get_device_service),
) -> PaginatedResponse[DeviceResponse]:
    items, total = await service.list_devices(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[DeviceResponse.model_validate(d) for d in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    device = await service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceResponse.model_validate(device)
