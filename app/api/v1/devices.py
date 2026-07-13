from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.common.enums import AssignmentStatus
from app.devices.models import Device
from app.devices.schemas import DeviceResponse, DeviceSearchCriteria
from app.common.schemas import PaginatedResponse
from app.profiles.models import Profile
from app.profiles.profile_assignment import ProfileAssignment

router = APIRouter(prefix="/devices", tags=["Devices"])


async def _batch_profile_names(db: AsyncSession, device_ids: list[int]) -> dict[int, list[str]]:
    if not device_ids:
        return {}
    stmt = (
        select(ProfileAssignment.device_id, Profile.name)
        .join(Profile, ProfileAssignment.profile_id == Profile.id)
        .where(
            ProfileAssignment.device_id.in_(device_ids),
            ProfileAssignment.status != AssignmentStatus.REMOVED,
        )
    )
    result = await db.execute(stmt)
    profiles_by_device: dict[int, list[str]] = defaultdict(list)
    for device_id, profile_name in result.all():
        profiles_by_device[device_id].append(profile_name)
    return dict(profiles_by_device)


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
        profiles=sorted(profiles),
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
    profiles_map = await _batch_profile_names(db, [d.id for d in items])
    return PaginatedResponse(
        items=[_to_response(d, profiles_map.get(d.id, [])) for d in items],
        total=total,
        skip=skip,
        limit=limit,
    )


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
    profiles_map = await _batch_profile_names(db, [device.id])
    return _to_response(device, profiles_map.get(device.id, []))


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
    profiles_map = await _batch_profile_names(db, [d.id for d in devices])
    return [_to_response(d, profiles_map.get(d.id, [])) for d in devices]
