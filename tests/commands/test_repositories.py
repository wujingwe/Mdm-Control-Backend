from app.commands.repositories import CommandRepository
from app.commands.schemas import CommandCreate
from app.common.enums import (
    CommandType,
    CommandStatus,
    ConnectionStatus,
    EnrollmentStatus,
)
from app.devices.models import Device
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_device(db_session: AsyncSession) -> Device:
    device = Device(
        name="Test Device",
        serial_number="SER001",
        os_version="15.0",
        connection_status=ConnectionStatus.ONLINE,
        enrollment_status=EnrollmentStatus.ENROLLED,
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


class TestCommandRepository:
    async def test_create(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        created = await repo.create(
            device_id=device.id,
            data=CommandCreate(command_type=CommandType.LOCK),
        )
        assert created.id is not None
        assert created.command_type == CommandType.LOCK
        assert created.status == CommandStatus.PENDING

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        created = await repo.create(
            device_id=device.id,
            data=CommandCreate(command_type=CommandType.LOCK),
        )
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.device_id == device.id

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = CommandRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_list_for_device(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        await repo.create(
            device_id=device.id, data=CommandCreate(command_type=CommandType.LOCK)
        )
        await repo.create(
            device_id=device.id, data=CommandCreate(command_type=CommandType.WIPE)
        )
        items = await repo.list_for_device(device.id)
        assert len(items) == 2

    async def test_mark_sent(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        created = await repo.create(
            device_id=device.id,
            data=CommandCreate(command_type=CommandType.LOCK),
        )
        updated = await repo.mark_sent(created.id, "msg-123")
        assert updated.status == CommandStatus.SENT

    async def test_update_status(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        created = await repo.create(
            device_id=device.id,
            data=CommandCreate(command_type=CommandType.LOCK),
        )
        updated = await repo.update_status(
            created.id, CommandStatus.COMPLETED, result_message="done"
        )
        assert updated.status == CommandStatus.COMPLETED
        assert updated.result_message == "done"

    async def test_cancel(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        created = await repo.create(
            device_id=device.id,
            data=CommandCreate(command_type=CommandType.LOCK),
        )
        updated = await repo.cancel(created.id)
        assert updated.status == CommandStatus.CANCELLED

    async def test_count_all(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        assert await repo.count_all() == 0
        await repo.create(
            device_id=device.id, data=CommandCreate(command_type=CommandType.LOCK)
        )
        assert await repo.count_all() == 1

    async def test_count_for_device(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        await repo.create(
            device_id=device.id, data=CommandCreate(command_type=CommandType.LOCK)
        )
        assert await repo.count_for_device(device.id) == 1
