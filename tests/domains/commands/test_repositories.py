from app.domains.commands.repositories import CommandRepository
from app.domains.commands.schemas import CommandCreate
from app.domains.commands.enums import CommandType, CommandStatus
from app.domains.devices.enums import ConnectionStatus, DeviceStatus
from app.domains.devices.models import Device
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_device(db_session: AsyncSession) -> Device:
    device = Device(
        name="Test Device",
        serial_number="SER001",
        os_version="15.0",
        connection_status=ConnectionStatus.CONNECTED,
        status=DeviceStatus.ENROLLED,
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
            created_by=1,
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
            created_by=1,
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
        await repo.create(device_id=device.id, data=CommandCreate(command_type=CommandType.LOCK), created_by=1)
        await repo.create(device_id=device.id, data=CommandCreate(command_type=CommandType.WIPE), created_by=1)
        items = await repo.list_for_device(device.id)
        assert len(items) == 2

    async def test_mark_sent(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        created = await repo.create(
            device_id=device.id,
            data=CommandCreate(command_type=CommandType.LOCK),
            created_by=1,
        )
        updated = await repo.mark_sent(created.id, "msg-123")
        assert updated.status == CommandStatus.SENT

    async def test_update_status(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        created = await repo.create(
            device_id=device.id,
            data=CommandCreate(command_type=CommandType.LOCK),
            created_by=1,
        )
        updated = await repo.update_status(created.id, CommandStatus.COMPLETED, result_message="done")
        assert updated.status == CommandStatus.COMPLETED
        assert updated.result_message == "done"

    async def test_update_status_reports_filters_by_device_and_updates_status_metadata(
        self, db_session: AsyncSession
    ) -> None:
        device = await _create_device(db_session)
        other_device = Device(
            name="Other Device",
            serial_number="SER002",
            os_version="15.0",
            connection_status=ConnectionStatus.CONNECTED,
            status=DeviceStatus.ENROLLED,
        )
        db_session.add(other_device)
        await db_session.commit()
        await db_session.refresh(other_device)

        repo = CommandRepository(db_session)
        completed = await repo.create(
            device_id=device.id, data=CommandCreate(command_type=CommandType.LOCK), created_by=1
        )
        acknowledged = await repo.create(
            device_id=device.id, data=CommandCreate(command_type=CommandType.WIPE), created_by=1
        )
        foreign = await repo.create(
            device_id=other_device.id, data=CommandCreate(command_type=CommandType.LOCK), created_by=1
        )

        await repo.update_status_reports(
            device.id,
            {
                completed.id: (CommandStatus.COMPLETED, "done"),
                acknowledged.id: (CommandStatus.ACKNOWLEDGED, None),
                foreign.id: (CommandStatus.COMPLETED, "must remain pending"),
            },
        )
        updated_completed = await repo.get_by_id(completed.id)
        updated_acknowledged = await repo.get_by_id(acknowledged.id)
        untouched_foreign = await repo.get_by_id(foreign.id)
        assert updated_completed is not None
        assert updated_completed.status == CommandStatus.COMPLETED
        assert updated_completed.result_message == "done"
        assert updated_completed.completed_at is not None
        assert updated_acknowledged is not None
        assert updated_acknowledged.status == CommandStatus.ACKNOWLEDGED
        assert updated_acknowledged.acknowledged_at is not None
        assert untouched_foreign is not None
        assert untouched_foreign.status == CommandStatus.PENDING

        await repo.update_status_reports(device.id, {})
        await repo.update_status_reports(device.id, {999: (CommandStatus.COMPLETED, "unknown")})

    async def test_count_all(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        assert await repo.count() == 0
        await repo.create(device_id=device.id, data=CommandCreate(command_type=CommandType.LOCK), created_by=1)
        assert await repo.count() == 1

    async def test_count_for_device(self, db_session: AsyncSession) -> None:
        device = await _create_device(db_session)
        repo = CommandRepository(db_session)
        await repo.create(device_id=device.id, data=CommandCreate(command_type=CommandType.LOCK), created_by=1)
        assert await repo.count_for_device(device.id) == 1
