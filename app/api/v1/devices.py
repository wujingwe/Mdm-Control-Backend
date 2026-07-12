from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.devices.models import Device
from app.devices.schemas import DeviceResponse, DeviceSearchCriteria
from app.common.schemas import PaginatedResponse
from app.profiles.models import Profile
from app.profiles.profile_assignment import ProfileAssignment

router = APIRouter(prefix="/devices", tags=["Devices"])


async def _profile_names(db: AsyncSession, device: Device) -> list[str]:
    stmt = (
        select(Profile.name)
        .join(ProfileAssignment, ProfileAssignment.profile_id == Profile.id)
        .where(
            ProfileAssignment.device_id == device.id,
            ProfileAssignment.status != "REMOVED",
        )
    )
    result = await db.execute(stmt)
    return sorted([r[0] for r in result.all()])


def _to_response(device: Device, profiles: list[str]) -> DeviceResponse:
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
        profiles=profiles,
    )


@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[DeviceResponse]:
    from app.devices.repositories import DeviceRepository
    from app.devices.services import DeviceService
    repo = DeviceRepository(db)
    service = DeviceService(repo)
    items, total = await service.list_devices(skip=skip, limit=limit)
    result = []
    for d in items:
        result.append(_to_response(d, await _profile_names(db, d)))
    return PaginatedResponse(items=result, total=total, skip=skip, limit=limit)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    db: AsyncSession = Depends(get_db),
) -> DeviceResponse:
    from app.devices.repositories import DeviceRepository
    from app.devices.services import DeviceService
    repo = DeviceRepository(db)
    service = DeviceService(repo)
    device = await service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return _to_response(device, await _profile_names(db, device))


@router.post("/search", response_model=list[DeviceResponse])
async def search_devices(
    criteria: DeviceSearchCriteria,
    db: AsyncSession = Depends(get_db),
) -> list[DeviceResponse]:
    from app.devices.repositories import DeviceRepository
    from app.devices.services import DeviceService
    repo = DeviceRepository(db)
    service = DeviceService(repo)
    devices = await service.search_devices(criteria)
    result = []
    for d in devices:
        result.append(_to_response(d, await _profile_names(db, d)))
    return result
