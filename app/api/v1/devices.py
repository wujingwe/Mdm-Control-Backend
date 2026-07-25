from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.commands.schemas import CommandCreate, CommandResponse
from app.commands.services import CommandService
from app.common.schemas import PaginatedResponse
from app.dependencies import get_command_service, get_device_service, get_reconciler, require_permission
from app.devices.schemas import DeviceResponse, DeviceUpdate
from app.devices.services import DeviceService
from app.profiles.reconciler import ProfileAssignmentReconciler
from app.users.models import User

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
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


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    data: DeviceUpdate,
    service: DeviceService = Depends(get_device_service),
    reconciler: ProfileAssignmentReconciler = Depends(get_reconciler),
) -> DeviceResponse:
    device = await service.update_device(device_id, data)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    await reconciler.recalculate_for_device(device_id)
    return DeviceResponse.model_validate(device)


@router.post("/{device_id}/check-in")
async def device_check_in(
    device_id: int,
    service: DeviceService = Depends(get_device_service),
    reconciler: ProfileAssignmentReconciler = Depends(get_reconciler),
) -> dict[str, str]:
    device = await service.get_device(device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    # Recalculate desired state first, then send one consolidated latest revision.
    await reconciler.recalculate_for_device(device_id, publish=False)
    await reconciler.reconcile_device(device_id)
    return {"status": "ok"}


@router.get("/{device_id}/commands", response_model=PaginatedResponse[CommandResponse])
async def list_device_commands(
    device_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: CommandService = Depends(get_command_service),
) -> PaginatedResponse[CommandResponse]:
    items, total = await service.list_device_commands(device_id, skip=skip, limit=limit)
    return PaginatedResponse(
        items=[CommandResponse.model_validate(c) for c in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{device_id}/commands/{command_id}", response_model=CommandResponse)
async def get_device_command(
    device_id: int,
    command_id: int,
    service: CommandService = Depends(get_command_service),
) -> CommandResponse:
    command = await service.get_command(command_id)
    if not command or command.device_id != device_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
    return CommandResponse.model_validate(command)


@router.post("/{device_id}/commands", response_model=CommandResponse, status_code=status.HTTP_201_CREATED)
async def execute_command(
    device_id: int,
    data: CommandCreate,
    service: CommandService = Depends(get_command_service),
    current_user: User = Depends(require_permission("editor")),
) -> CommandResponse:
    result = await service.trigger_command(device_id, data, current_user.id)
    command = result["command"]
    return CommandResponse.model_validate(command)
