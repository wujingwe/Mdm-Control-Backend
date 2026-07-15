from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.commands.schemas import CommandCreate, CommandResponse
from app.commands.services import CommandService
from app.common.schemas import Message, PaginatedResponse
from app.dependencies import get_command_service

router = APIRouter(prefix="/devices/{device_id}/commands", tags=["Commands"])


@router.get("", response_model=PaginatedResponse[CommandResponse])
async def list_device_commands(
    device_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    service: CommandService = Depends(get_command_service),
) -> PaginatedResponse[CommandResponse]:
    items, total = await service.list_device_commands(device_id, skip=skip, limit=limit)
    return PaginatedResponse(
        items=[CommandResponse.model_validate(c) for c in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{command_id}", response_model=CommandResponse)
async def get_device_command(
    device_id: int,
    command_id: int,
    service: CommandService = Depends(get_command_service),
) -> CommandResponse:
    command = await service.get_command(command_id)
    if not command or command.device_id != device_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")
    return CommandResponse.model_validate(command)


@router.post("", response_model=CommandResponse, status_code=201)
async def trigger_device_command(
    device_id: int,
    data: CommandCreate,
    service: CommandService = Depends(get_command_service),
) -> CommandResponse:
    result = await service.trigger_command(device_id, data)
    command = result["command"]
    return CommandResponse.model_validate(command)


@router.delete("/{command_id}", response_model=Message)
async def cancel_device_command(
    device_id: int,
    command_id: int,
    service: CommandService = Depends(get_command_service),
) -> Message:
    command = await service.get_command(command_id)
    if not command or command.device_id != device_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found")

    cancelled = await service.cancel_command(command_id)
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Command cannot be cancelled in its current state",
        )
    return Message(detail="Command cancelled")
