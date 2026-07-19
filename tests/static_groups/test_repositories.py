import pytest
from app.core.exceptions import ConflictError
from app.static_groups.repositories import StaticGroupRepository
from app.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate
from sqlalchemy.ext.asyncio import AsyncSession


class TestStaticGroupRepository:
    async def test_create(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        assert created.id is not None
        assert created.name == "SG1"
        assert created.created_by == 1
        assert created.description is None

    async def test_create_with_description(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        created = await repo.create(
            StaticGroupCreate(
                name="SG1",
                description="Test description",
                created_by=1,
            )
        )
        assert created.description == "Test description"

    async def test_create_without_devices(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        group = await repo.create(StaticGroupCreate(name="SG1", created_by=1))

        result = await repo.get_by_id(group.id)
        assert result is not None
        serials = [x.serial_number for x in result.devices]
        assert serials == []

    async def test_create_with_devices(self, db_session: AsyncSession) -> None:
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(
            name="D1",
            serial_number="SN001",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev2 = Device(
            name="D2",
            serial_number="SN002",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev3 = Device(
            name="D3",
            serial_number="SN003",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()

        group = await repo.create(
            StaticGroupCreate(
                name="SG1",
                created_by=1,
                device_serial_numbers=["SN001", "SN002", "SN003"],
            )
        )

        result = await repo.get_by_id(group.id)
        assert result is not None
        serials = [x.serial_number for x in result.devices]
        assert set(serials) == {"SN001", "SN002", "SN003"}

    async def test_create_duplicate_name_raises(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        with pytest.raises(ConflictError):
            await repo.create(StaticGroupCreate(name="SG1", created_by=2))

    async def test_list_empty(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        items = await repo.list_all()
        assert items == []

    async def test_list(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        await repo.create(StaticGroupCreate(name="SG2", created_by=1))
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_ordering(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        sg2 = await repo.create(StaticGroupCreate(name="SG2", created_by=1))
        sg1 = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        items = await repo.list_all()
        assert items[0].id == sg2.id
        assert items[1].id == sg1.id

    async def test_list_pagination(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        for i in range(5):
            await repo.create(StaticGroupCreate(name=f"SG{i}", created_by=1))
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_list_pagination_empty(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        for i in range(3):
            await repo.create(StaticGroupCreate(name=f"SG{i}", created_by=1))
        items = await repo.list_all(skip=10, limit=10)
        assert items == []

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "SG1"

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update_name(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        updated = await repo.update(created.id, StaticGroupUpdate(name="SG2"))
        assert updated is not None
        assert updated.name == "SG2"

    async def test_update_description(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        updated = await repo.update(
            created.id, StaticGroupUpdate(description="New desc")
        )
        assert updated is not None
        assert updated.description == "New desc"

    async def test_update_name_and_description(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        updated = await repo.update(
            created.id,
            StaticGroupUpdate(
                name="SG2",
                description="New desc",
            ),
        )
        assert updated is not None
        assert updated.name == "SG2"
        assert updated.description == "New desc"

    async def test_update_empty_body_returns_same(
        self, db_session: AsyncSession
    ) -> None:
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        updated = await repo.update(created.id, StaticGroupUpdate())
        assert updated is not None
        assert updated.id == created.id
        assert updated.name == "SG1"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        assert await repo.update(999, StaticGroupUpdate(name="x")) is None

    async def test_update_duplicate_name_raises(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        sg2 = await repo.create(StaticGroupCreate(name="SG2", created_by=1))
        with pytest.raises(ConflictError):
            await repo.update(sg2.id, StaticGroupUpdate(name="SG1"))

    async def test_update_device_serial_numbers(self, db_session: AsyncSession) -> None:
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(
            name="D1",
            serial_number="SN001",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev2 = Device(
            name="D2",
            serial_number="SN002",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev3 = Device(
            name="D3",
            serial_number="SN003",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()

        group = await repo.create(
            StaticGroupCreate(
                name="SG1",
                created_by=1,
                device_serial_numbers=["SN001", "SN002"],
            )
        )
        await repo.update(group.id, StaticGroupUpdate(device_serial_numbers=["SN003"]))

        result = await repo.get_by_id(group.id)
        assert result is not None
        serials = [x.serial_number for x in result.devices]
        assert serials == ["SN003"]

    async def test_update_replaces_all_devices(self, db_session: AsyncSession) -> None:
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(
            name="D1",
            serial_number="SN001",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev2 = Device(
            name="D2",
            serial_number="SN002",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        db_session.add_all([dev1, dev2])
        await db_session.commit()

        group = await repo.create(
            StaticGroupCreate(
                name="SG1",
                created_by=1,
                device_serial_numbers=["SN001"],
            )
        )
        await repo.update(group.id, StaticGroupUpdate(device_serial_numbers=["SN002"]))

        result = await repo.get_by_id(group.id)
        assert result is not None
        serials = [x.serial_number for x in result.devices]
        assert serials == ["SN002"]

    async def test_update_with_empty_device_list(
        self, db_session: AsyncSession
    ) -> None:
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(
            name="D1",
            serial_number="SN001",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        db_session.add(dev1)
        await db_session.commit()

        group = await repo.create(
            StaticGroupCreate(
                name="SG1",
                created_by=1,
                device_serial_numbers=["SN001"],
            )
        )
        await repo.update(group.id, StaticGroupUpdate(device_serial_numbers=[]))

        result = await repo.get_by_id(group.id)
        assert result is not None
        serials = [x.serial_number for x in result.devices]
        assert serials == []

    async def test_update_name_and_devices_together(
        self, db_session: AsyncSession
    ) -> None:
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(
            name="D1",
            serial_number="SN001",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev2 = Device(
            name="D2",
            serial_number="SN002",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        db_session.add_all([dev1, dev2])
        await db_session.commit()

        group = await repo.create(
            StaticGroupCreate(
                name="SG1",
                created_by=1,
                device_serial_numbers=["SN001"],
            )
        )
        updated = await repo.update(
            group.id,
            StaticGroupUpdate(
                name="SG2",
                device_serial_numbers=["SN002"],
            ),
        )
        assert updated.name == "SG2"

        result = await repo.get_by_id(group.id)
        assert result is not None
        serials = [x.serial_number for x in result.devices]
        assert serials == ["SN002"]

    async def test_update_devices_twice(self, db_session: AsyncSession) -> None:
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(
            name="D1",
            serial_number="SN001",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev2 = Device(
            name="D2",
            serial_number="SN002",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev3 = Device(
            name="D3",
            serial_number="SN003",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()

        group = await repo.create(
            StaticGroupCreate(
                name="SG1",
                created_by=1,
                device_serial_numbers=["SN001"],
            )
        )
        await repo.update(
            group.id,
            StaticGroupUpdate(
                device_serial_numbers=["SN001", "SN002"],
            ),
        )
        await repo.update(
            group.id,
            StaticGroupUpdate(
                device_serial_numbers=["SN003"],
            ),
        )

        result = await repo.get_by_id(group.id)
        assert result is not None
        serials = [x.serial_number for x in result.devices]
        assert serials == ["SN003"]

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        assert await repo.count() == 0
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        assert await repo.count() == 1

    async def test_count_multiple(self, db_session: AsyncSession) -> None:
        repo = StaticGroupRepository(db_session)
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        await repo.create(StaticGroupCreate(name="SG2", created_by=1))
        await repo.create(StaticGroupCreate(name="SG3", created_by=1))
        assert await repo.count() == 3
