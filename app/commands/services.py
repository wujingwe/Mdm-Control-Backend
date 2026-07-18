from __future__ import annotations

import logging

from app.commands.models import Command
from app.commands.repositories import CommandRepository
from app.commands.schemas import CommandCreate
from app.messaging.producer import rabbitmq_producer

logger = logging.getLogger(__name__)


class CommandService:
    def __init__(self, repo: CommandRepository) -> None:
        self.repo = repo

    async def trigger_command(
        self,
        device_id: int,
        data: CommandCreate,
        created_by: int | None = None,
    ) -> dict[str, object]:
        command = await self.repo.create(device_id, data, created_by)
        event_type = f"device.command.{data.command_type.value.lower()}"

        try:
            message_id = await rabbitmq_producer.publish_device_command(
                device_id=device_id,
                command_id=command.id,
                command_type=data.command_type.value,
                parameters={},
                event_type=event_type,
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

    async def list_commands(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[Command], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count_all()
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
