from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_device_service
from app.devices.models import Device
from app.devices.schemas import DeviceResponse, DeviceSearchCriteria
from app.common.schemas import PaginatedResponse
from app.devices.services import DeviceService
from app.webhook_client import revalidate

router = APIRouter(prefix="/devices", tags=["Devices"])


async def _policy_names(device: Device) -> list[str]:
    return sorted([p.name for p in device.policies])


def _to_response(device: Device, policies: list[str]) -> DeviceResponse:
    return DeviceResponse(
        id=device.id,
        name=device.name,
        serial_number=device.serial_number,
        os_version=device.os_version,
        connection_status=device.connection_status,
        enrollment_status=device.enrollment_status,
        created_at=device.created_at,
        updated_at=device.updated_at,
        last_enrolled_at=device.last_enrolled_at,
        battery_status=device.battery_status,
        total_storage=device.total_storage,
        available_storage=device.available_storage,
        total_memory=device.total_memory,
        available_memory=device.available_memory,
        network=device.network,
        certificates=device.certificates,
        policies=policies,
    )


@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
    service: DeviceService = Depends(get_device_service),
) -> PaginatedResponse[DeviceResponse]:
    items, total = await service.list_devices(skip=skip, limit=limit)
    result = []
    for d in items:
        result.append(_to_response(d, await _policy_names(d)))
    return PaginatedResponse(items=result, total=total, skip=skip, limit=limit)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    device = await service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return _to_response(device, await _policy_names(device))


@router.post("/search", response_model=list[DeviceResponse])
async def search_devices(
    criteria: DeviceSearchCriteria,
    service: DeviceService = Depends(get_device_service),
) -> list[DeviceResponse]:
    devices = await service.search_devices(criteria)
    result = []
    for d in devices:
        result.append(_to_response(d, await _policy_names(d)))
    return result


@router.post("/{device_id}/policy", response_model=DeviceResponse)
async def assign_policy(
    device_id: int,
    policy_id: int = Query(...),
    service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    device = await service.assign_policy(device_id, policy_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await revalidate(["devices"])
    return _to_response(device, await _policy_names(device))
