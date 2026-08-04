from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.domains.commands.schemas import CommandCreate, CommandResponse, CommandStatusUpdate
from app.domains.commands.services import CommandService
from app.infra.common.schemas import PaginatedResponse
from app.dependencies import get_command_service, get_device_service, require_permission
from app.domains.devices.schemas import DeviceResponse, DeviceUpdate
from app.domains.devices.services import DeviceService
from app.domains.users.models import User

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
    _current_user: User = Depends(require_permission("editor")),
) -> DeviceResponse:
    if not data.model_fields_set:
        device = await service.get_device(device_id)
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
        return DeviceResponse.model_validate(device)
    updated = await service.update_device(device_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    device = await service.get_device(device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceResponse.model_validate(device)


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


@router.put("/{device_id}/commands/{command_id}/status", response_model=CommandResponse)
async def update_command_status(
    device_id: int,
    command_id: int,
    data: CommandStatusUpdate,
    service: CommandService = Depends(get_command_service),
    _current_user: User = Depends(require_permission("editor")),
) -> CommandResponse:
    command = await service.update_status(command_id, data.status, data.result_message)
    if not command or command.device_id != device_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
    return CommandResponse.model_validate(command)
