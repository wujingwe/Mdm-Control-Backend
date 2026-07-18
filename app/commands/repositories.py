from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.commands.models import Command
from app.commands.schemas import CommandCreate
from app.common.enums import CommandStatus


class CommandRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        device_id: int,
        data: CommandCreate,
        created_by: int | None = None,
    ) -> Command:
        instance = Command(
            device_id=device_id,
            command_type=data.command_type,
            status=CommandStatus.PENDING,
            created_by=created_by,
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def get_by_id(self, command_id: int) -> Command | None:
        stmt = select(Command).where(Command.id == command_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_device(
        self,
        device_id: int,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Command]:
        stmt = (
            select(Command)
            .where(Command.device_id == device_id)
            .order_by(Command.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_for_device(self, device_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Command)
            .where(Command.device_id == device_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> list[Command]:
        stmt = select(Command).order_by(Command.id.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        stmt = select(func.count()).select_from(Command)
        result = await self.db.execute(stmt)
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
            .returning(Command)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalars().one_or_none()

    async def update_status(
        self,
        command_id: int,
        status: CommandStatus,
        result_message: str | None = None,
    ) -> Command | None:
        now = datetime.now(timezone.utc)
        values: dict = {"status": status}
        if result_message is not None:
            values["result_message"] = result_message
        if status == CommandStatus.COMPLETED:
            values["completed_at"] = now
        elif status == CommandStatus.ACKNOWLEDGED:
            values["acknowledged_at"] = now

        stmt = (
            update(Command)
            .where(Command.id == command_id)
            .values(**values)
            .returning(Command)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalars().one_or_none()

    async def cancel(self, command_id: int) -> Command | None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Command)
            .where(
                Command.id == command_id,
                Command.status.in_([CommandStatus.PENDING, CommandStatus.SENT]),
            )
            .values(
                status=CommandStatus.CANCELLED,
                completed_at=now,
                result_message="Cancelled by administrator",
            )
            .returning(Command)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalars().one_or_none()
