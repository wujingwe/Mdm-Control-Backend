import pytest
from app.core.exceptions import ConflictError
from app.devices.repositories import DeviceRepository
from app.smart_groups.repositories import SmartGroupRepository
from app.smart_groups.schemas import SmartGroupCreate, SmartGroupUpdate
from app.static_groups.repositories import StaticGroupRepository
from app.static_groups.schemas import StaticGroupCreate, StaticGroupUpdate
from app.users.repositories import UserRepository
from app.users.schemas import UserCreateDB, UserUpdateDB
from app.extension_attributes.repositories import ExtensionAttributeRepository
from app.extension_attributes.schemas import ExtensionAttributeCreate, ExtensionAttributeUpdate
from app.inventory_search.repositories import InventorySearchRepository
from app.inventory_search.schemas import InventorySearchCreate, InventorySearchUpdate
from app.devices.schemas import Certificate, Cellular, Network, Wifi
from app.common.enums import ExtensionDataType, ExtensionInputType


def _make_device_data(serial: str = "SN001", name: str = "Test Device") -> dict:
    return {
        "name": name,
        "serial_number": serial,
        "os_version": "14.0",
        "connection_status": "Online",
        "enrollment_status": "Enrolled",
    }


class TestDeviceRepository:
    async def test_create(self, db_session):
        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        assert device.id is not None
        assert device.serial_number == "SN001"
        assert device.name == "Test Device"

    async def test_get_by_id(self, db_session):
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.serial_number == "SN001"

    async def test_get_by_id_not_found(self, db_session):
        repo = DeviceRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session):
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        updated = await repo.update(created.id, {"name": "New", "connection_status": "Offline"})
        assert updated is not None
        assert updated.name == "New"
        assert updated.connection_status == "Offline"
        assert updated.serial_number == "SN001"

    async def test_update_not_found(self, db_session):
        repo = DeviceRepository(db_session)
        assert await repo.update(999, {"name": "X"}) is None

    async def test_delete(self, db_session):
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = DeviceRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session):
        repo = DeviceRepository(db_session)
        assert await repo.count() == 0
        await repo.create(_make_device_data())
        assert await repo.count() == 1

    async def test_unique_serial(self, db_session):
        repo = DeviceRepository(db_session)
        await repo.create(_make_device_data())
        with pytest.raises(ConflictError):
            await repo.create(_make_device_data())

    async def test_create_with_network_and_certificates(self, db_session):
        repo = DeviceRepository(db_session)
        data = _make_device_data()
        data["network"] = Network(wifi=Wifi(ssid="Office", bssid="00:11:22:33:44:55"))
        data["certificates"] = [Certificate(common_name="example.com", issuer="CA Inc")]
        device = await repo.create(data)
        assert device.id is not None
        assert device.network is not None
        assert device.network.wifi.ssid == "Office"
        assert device.network.wifi.bssid == "00:11:22:33:44:55"
        assert device.network.cellular is None
        assert len(device.certificates) == 1
        assert device.certificates[0].common_name == "example.com"
        assert device.certificates[0].issuer == "CA Inc"

    async def test_update_network(self, db_session):
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        updated = await repo.update(created.id, {
            "network": Network(wifi=Wifi(ssid="Updated"), cellular=Cellular(carrier="Verizon")),
        })
        assert updated.network.wifi.ssid == "Updated"
        assert updated.network.cellular.carrier == "Verizon"


class TestSmartGroupRepository:
    async def test_crud(self, db_session):
        repo = SmartGroupRepository(db_session)
        created = await repo.create(SmartGroupCreate(name="Group A", created_by=1))
        assert created.id is not None

        found = await repo.get_by_id(created.id)
        assert found.name == "Group A"

        updated = await repo.update(created.id, SmartGroupUpdate(description="desc"))
        assert updated.description == "desc"

        assert await repo.count() == 1


class TestUserRepository:
    async def test_crud(self, db_session):
        repo = UserRepository(db_session)
        created = await repo.create(UserCreateDB(
            email="j@example.com",
            name="jdoe",
            password_hash="hashed_secret",
            permissions=frozenset({"admin"}),
        ))
        assert created.id is not None
        assert created.name == "jdoe"

        found = await repo.get_by_id(created.id)
        assert found.email == "j@example.com"

        assert await repo.delete(created.id) is True

    async def test_list(self, db_session):
        repo = UserRepository(db_session)
        base = dict(password_hash="h", permissions=frozenset({"viewer"}))
        await repo.create(UserCreateDB(email="u1@e.com", name="u1", **base))
        await repo.create(UserCreateDB(email="u2@e.com", name="u2", **base))
        assert len(await repo.list_all()) == 2

    async def test_update(self, db_session):
        repo = UserRepository(db_session)
        created = await repo.create(UserCreateDB(
            email="upd@example.com", name="orig",
            password_hash="h", permissions=frozenset({"viewer"}),
        ))
        updated = await repo.update(created.id, UserUpdateDB(name="updated"))
        assert updated is not None
        assert updated.name == "updated"

    async def test_update_not_found(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.update(999, UserUpdateDB(name="x")) is None

    async def test_count(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.count() == 0
        await repo.create(UserCreateDB(
            email="c@e.com", name="c",
            password_hash="h", permissions=frozenset({"viewer"}),
        ))
        assert await repo.count() == 1

    async def test_list_pagination(self, db_session):
        repo = UserRepository(db_session)
        base = dict(password_hash="h", permissions=frozenset({"viewer"}))
        for i in range(5):
            await repo.create(UserCreateDB(email=f"u{i}@e.com", name=f"u{i}", **base))
        items = await repo.list_all(skip=2, limit=2)
        assert len(items) == 2

    async def test_delete_not_found(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.delete(999) is False


class TestSmartGroupRepositoryExtended:
    async def test_delete(self, db_session):
        repo = SmartGroupRepository(db_session)
        created = await repo.create(SmartGroupCreate(name="G", created_by=1))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = SmartGroupRepository(db_session)
        assert await repo.delete(999) is False

    async def test_get_by_id_not_found(self, db_session):
        repo = SmartGroupRepository(db_session)
        assert await repo.get_by_id(999) is None


class TestStaticGroupRepository:
    async def test_create(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        assert created.id is not None
        assert created.name == "SG1"
        assert created.created_by == 1
        assert created.description is None

    async def test_create_with_description(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(
            name="SG1",
            description="Test description",
            created_by=1,
        ))
        assert created.description == "Test description"

    async def test_create_without_devices(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        serials = await repo.get_device_serial_numbers(created.id)
        assert serials == []

    async def test_create_with_devices(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev3 = Device(name="D3", serial_number="SN003", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()

        group = await repo.create(StaticGroupCreate(
            name="SG1",
            created_by=1,
            device_serial_numbers=["SN001", "SN002", "SN003"],
        ))
        serials = await repo.get_device_serial_numbers(group.id)
        assert set(serials) == {"SN001", "SN002", "SN003"}

    async def test_create_duplicate_name_raises(self, db_session):
        repo = StaticGroupRepository(db_session)
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        with pytest.raises(ConflictError):
            await repo.create(StaticGroupCreate(name="SG1", created_by=2))

    async def test_list_empty(self, db_session):
        repo = StaticGroupRepository(db_session)
        items = await repo.list_all()
        assert items == []

    async def test_list(self, db_session):
        repo = StaticGroupRepository(db_session)
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        await repo.create(StaticGroupCreate(name="SG2", created_by=1))
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_ordering(self, db_session):
        repo = StaticGroupRepository(db_session)
        sg2 = await repo.create(StaticGroupCreate(name="SG2", created_by=1))
        sg1 = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        items = await repo.list_all()
        assert items[0].id == sg2.id
        assert items[1].id == sg1.id

    async def test_list_pagination(self, db_session):
        repo = StaticGroupRepository(db_session)
        for i in range(5):
            await repo.create(StaticGroupCreate(name=f"SG{i}", created_by=1))
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_list_pagination_empty(self, db_session):
        repo = StaticGroupRepository(db_session)
        for i in range(3):
            await repo.create(StaticGroupCreate(name=f"SG{i}", created_by=1))
        items = await repo.list_all(skip=10, limit=10)
        assert items == []

    async def test_get_by_id(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "SG1"

    async def test_get_by_id_not_found(self, db_session):
        repo = StaticGroupRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update_name(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        updated = await repo.update(created.id, StaticGroupUpdate(name="SG2"))
        assert updated is not None
        assert updated.name == "SG2"

    async def test_update_description(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        updated = await repo.update(created.id, StaticGroupUpdate(description="New desc"))
        assert updated is not None
        assert updated.description == "New desc"

    async def test_update_name_and_description(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        updated = await repo.update(created.id, StaticGroupUpdate(
            name="SG2",
            description="New desc",
        ))
        assert updated is not None
        assert updated.name == "SG2"
        assert updated.description == "New desc"

    async def test_update_empty_body_returns_same(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        updated = await repo.update(created.id, StaticGroupUpdate())
        assert updated is not None
        assert updated.id == created.id
        assert updated.name == "SG1"

    async def test_update_not_found(self, db_session):
        repo = StaticGroupRepository(db_session)
        assert await repo.update(999, StaticGroupUpdate(name="x")) is None

    async def test_update_duplicate_name_raises(self, db_session):
        repo = StaticGroupRepository(db_session)
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        sg2 = await repo.create(StaticGroupCreate(name="SG2", created_by=1))
        with pytest.raises(ConflictError):
            await repo.update(sg2.id, StaticGroupUpdate(name="SG1"))

    async def test_update_device_serial_numbers(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev3 = Device(name="D3", serial_number="SN003", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()

        group = await repo.create(StaticGroupCreate(
            name="SG1",
            created_by=1,
            device_serial_numbers=["SN001", "SN002"],
        ))
        await repo.update(group.id, StaticGroupUpdate(device_serial_numbers=["SN003"]))
        serials = await repo.get_device_serial_numbers(group.id)
        assert serials == ["SN003"]

    async def test_update_replaces_all_devices(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2])
        await db_session.commit()

        group = await repo.create(StaticGroupCreate(
            name="SG1",
            created_by=1,
            device_serial_numbers=["SN001"],
        ))
        await repo.update(group.id, StaticGroupUpdate(device_serial_numbers=["SN002"]))
        serials = await repo.get_device_serial_numbers(group.id)
        assert serials == ["SN002"]

    async def test_update_with_empty_device_list(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add(dev1)
        await db_session.commit()

        group = await repo.create(StaticGroupCreate(
            name="SG1",
            created_by=1,
            device_serial_numbers=["SN001"],
        ))
        await repo.update(group.id, StaticGroupUpdate(device_serial_numbers=[]))
        serials = await repo.get_device_serial_numbers(group.id)
        assert serials == []

    async def test_update_name_and_devices_together(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2])
        await db_session.commit()

        group = await repo.create(StaticGroupCreate(
            name="SG1",
            created_by=1,
            device_serial_numbers=["SN001"],
        ))
        updated = await repo.update(group.id, StaticGroupUpdate(
            name="SG2",
            device_serial_numbers=["SN002"],
        ))
        assert updated.name == "SG2"
        serials = await repo.get_device_serial_numbers(group.id)
        assert serials == ["SN002"]

    async def test_delete(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = StaticGroupRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session):
        repo = StaticGroupRepository(db_session)
        assert await repo.count() == 0
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        assert await repo.count() == 1

    async def test_count_multiple(self, db_session):
        repo = StaticGroupRepository(db_session)
        await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        await repo.create(StaticGroupCreate(name="SG2", created_by=1))
        await repo.create(StaticGroupCreate(name="SG3", created_by=1))
        assert await repo.count() == 3

    async def test_get_device_serial_numbers(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2])
        await db_session.commit()

        group = await repo.create(StaticGroupCreate(
            name="SG1",
            created_by=1,
            device_serial_numbers=["SN001", "SN002"],
        ))
        serials = await repo.get_device_serial_numbers(group.id)
        assert set(serials) == {"SN001", "SN002"}

    async def test_get_device_serial_numbers_empty(self, db_session):
        repo = StaticGroupRepository(db_session)
        group = await repo.create(StaticGroupCreate(name="SG1", created_by=1))
        serials = await repo.get_device_serial_numbers(group.id)
        assert serials == []

    async def test_get_device_serial_numbers_not_found(self, db_session):
        repo = StaticGroupRepository(db_session)
        serials = await repo.get_device_serial_numbers(999)
        assert serials == []


class TestInventorySearchRepository:
    async def test_create(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="search1", created_by=1))
        assert created.id is not None
        assert created.name == "search1"

    async def test_list(self, db_session):
        repo = InventorySearchRepository(db_session)
        await repo.create(InventorySearchCreate(name="s1", created_by=1))
        await repo.create(InventorySearchCreate(name="s2", created_by=1))
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session):
        repo = InventorySearchRepository(db_session)
        for i in range(5):
            await repo.create(InventorySearchCreate(name=f"s{i}", created_by=1))
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", created_by=1))
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "s1"

    async def test_get_by_id_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", created_by=1))
        updated = await repo.update(created.id, InventorySearchUpdate(name="s2"))
        assert updated is not None
        assert updated.name == "s2"

    async def test_update_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.update(999, InventorySearchUpdate(name="x")) is None

    async def test_delete(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create(InventorySearchCreate(name="s1", created_by=1))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.count() == 0
        await repo.create(InventorySearchCreate(name="s1", created_by=1))
        assert await repo.count() == 1


class TestExtensionAttributeRepository:
    async def test_create(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(ExtensionAttributeCreate(
            name="ext1", data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD, created_by=1,
        ))
        assert created.id is not None
        assert created.name == "ext1"

    async def test_create_unique_name(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        data = ExtensionAttributeCreate(
            name="ext1", data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD, created_by=1,
        )
        await repo.create(data)
        with pytest.raises(ConflictError):
            await repo.create(data)

    async def test_list(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        base = dict(data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD, created_by=1)
        await repo.create(ExtensionAttributeCreate(name="ext1", **base))
        await repo.create(ExtensionAttributeCreate(name="ext2", **base))
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        base = dict(data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD, created_by=1)
        for i in range(5):
            await repo.create(ExtensionAttributeCreate(name=f"ext{i}", **base))
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(ExtensionAttributeCreate(
            name="ext1", data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD, created_by=1,
        ))
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "ext1"

    async def test_get_by_id_not_found(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(ExtensionAttributeCreate(
            name="ext1", data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD, created_by=1,
        ))
        updated = await repo.update(created.id, ExtensionAttributeUpdate(name="ext2"))
        assert updated is not None
        assert updated.name == "ext2"

    async def test_update_not_found(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.update(999, ExtensionAttributeUpdate(name="x")) is None

    async def test_delete(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create(ExtensionAttributeCreate(
            name="ext1", data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD, created_by=1,
        ))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.count() == 0
        await repo.create(ExtensionAttributeCreate(
            name="ext1", data_type=ExtensionDataType.STRING, input_type=ExtensionInputType.TEXT_FIELD, created_by=1,
        ))
        assert await repo.count() == 1
