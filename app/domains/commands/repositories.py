from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.commands.models import Command
from app.domains.commands.schemas import CommandCreate
from app.domains.commands.enums import CommandStatus
from app.infra.core.exceptions import ConflictError


class CommandRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_device(
        self,
        device_id: int,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Command]:
        stmt = (
            select(Command).where(Command.device_id == device_id).order_by(Command.id.desc()).offset(skip).limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, command_id: int) -> Command | None:
        stmt = select(Command).where(Command.id == command_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        device_id: int,
        data: CommandCreate,
        created_by: int,
    ) -> Command:
        instance = Command(**data.model_dump(), device_id=device_id, created_by=created_by)
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Command integrity error") from err
        return instance

    async def count_for_device(self, device_id: int) -> int:
        stmt = select(func.count()).select_from(Command).where(Command.device_id == device_id)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def list(self, *, skip: int = 0, limit: int = 100) -> list[Command]:
        stmt = select(Command).order_by(Command.id.desc()).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Command)
        result = await self._db.execute(stmt)
        return result.scalar_one()

    async def mark_sent(
        self,
        command_id: int,
        rabbitmq_message_id: str,
    ) -> Command | None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Command)
            .where(
                Command.id == command_id,
                Command.status == CommandStatus.PENDING,
            )
            .values(
                status=CommandStatus.SENT,
                sent_at=now,
                rabbitmq_message_id=rabbitmq_message_id,
            )
        )
        await self._db.execute(stmt)
        await self._db.commit()
        return await self.get_by_id(command_id)

    async def update_status(
        self,
        command_id: int,
        status: CommandStatus,
        result_message: str | None = None,
    ) -> Command | None:
        now = datetime.now(timezone.utc)
        values: dict[str, Any] = {"status": status}
        if result_message is not None:
            values["result_message"] = result_message
        if status == CommandStatus.COMPLETED:
            values["completed_at"] = now
        elif status == CommandStatus.ACKNOWLEDGED:
            values["acknowledged_at"] = now

        stmt = update(Command).where(Command.id == command_id).values(**values)
        await self._db.execute(stmt)
        await self._db.commit()
        return await self.get_by_id(command_id)
