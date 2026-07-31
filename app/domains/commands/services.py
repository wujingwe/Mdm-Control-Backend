from __future__ import annotations

import logging

from app.domains.commands.enums import CommandStatus
from app.domains.commands.models import Command
from app.domains.commands.repositories import CommandRepository
from app.domains.commands.schemas import CommandCreate
from app.domains.devices.repositories import DeviceRepository
from app.infra.messaging.producer import rabbitmq_producer

logger = logging.getLogger(__name__)


class CommandService:
    def __init__(self, repo: CommandRepository, device_repo: DeviceRepository) -> None:
        self.repo = repo
        self.device_repo = device_repo

    async def trigger_command(
        self,
        device_id: int,
        data: CommandCreate,
        created_by: int,
    ) -> dict[str, object]:
        command = await self.repo.create(device_id, data, created_by)

        serial = await self.device_repo.get_serial_number(device_id)
        if not serial:
            logger.warning("Device %s not found when publishing command", device_id)
            return {"command": command, "message_id": None}

        try:
            message_id = await rabbitmq_producer.publish_device_command(
                serial_number=serial,
                command_id=command.id,
                command_type=data.command_type.value,
                parameters={},
            )
            updated = await self.repo.mark_sent(command.id, message_id)
            if updated is not None:
                return {"command": updated, "message_id": message_id}
            return {"command": command, "message_id": message_id}
        except Exception:
            logger.exception("Failed to publish command %s", command.id)
            return {"command": command, "message_id": None}

    async def get_command(self, command_id: int) -> Command | None:
        return await self.repo.get_by_id(command_id)

    async def update_status(
        self,
        command_id: int,
        status: CommandStatus,
        result_message: str | None = None,
    ) -> Command | None:
        return await self.repo.update_status(command_id, status, result_message)

    async def list_commands(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Command], int]:
        items = await self.repo.list(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def list_device_commands(
        self,
        device_id: int,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Command], int]:
        items = await self.repo.list_for_device(device_id, skip=skip, limit=limit)
        total = await self.repo.count_for_device(device_id)
        return items, total
