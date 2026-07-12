import pytest
from app.core.exceptions import ConflictError
from app.devices.repositories import DeviceRepository
from app.smart_groups.repositories import SmartGroupRepository
from app.static_groups.repositories import StaticGroupRepository
from app.static_groups.static_group_device import StaticGroupDevice
from app.users.repositories import UserRepository
from app.extension_attributes.repositories import ExtensionAttributeRepository
from app.inventory_search.repositories import InventorySearchRepository
from app.devices.schemas import Certificate, Cellular, Network, Wifi


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
        created = await repo.create({"name": "Group A", "created_by": 1})
        assert created.id is not None

        found = await repo.get_by_id(created.id)
        assert found.name == "Group A"

        updated = await repo.update(created.id, {"description": "desc"})
        assert updated.description == "desc"

        assert await repo.count() == 1


class TestUserRepository:
    async def test_crud(self, db_session):
        repo = UserRepository(db_session)
        created = await repo.create({
            "email": "j@example.com",
            "name": "jdoe",
            "password_hash": "hashed_secret",
            "permissions": ["admin"],
        })
        assert created.id is not None
        assert created.name == "jdoe"

        found = await repo.get_by_id(created.id)
        assert found.email == "j@example.com"

        assert await repo.delete(created.id) is True

    async def test_list(self, db_session):
        repo = UserRepository(db_session)
        base = {"password_hash": "h", "permissions": ["viewer"]}
        await repo.create({"email": "u1@e.com", "name": "u1", **base})
        await repo.create({"email": "u2@e.com", "name": "u2", **base})
        assert len(await repo.list_all()) == 2

    async def test_update(self, db_session):
        repo = UserRepository(db_session)
        created = await repo.create({
            "email": "upd@example.com", "name": "orig",
            "password_hash": "h", "permissions": ["viewer"],
        })
        updated = await repo.update(created.id, {"name": "updated"})
        assert updated is not None
        assert updated.name == "updated"

    async def test_update_not_found(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.update(999, {"name": "x"}) is None

    async def test_count(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.count() == 0
        await repo.create({
            "email": "c@e.com", "name": "c",
            "password_hash": "h", "permissions": ["viewer"],
        })
        assert await repo.count() == 1

    async def test_list_pagination(self, db_session):
        repo = UserRepository(db_session)
        base = {"password_hash": "h", "permissions": ["viewer"]}
        for i in range(5):
            await repo.create({"email": f"u{i}@e.com", "name": f"u{i}", **base})
        items = await repo.list_all(skip=2, limit=2)
        assert len(items) == 2

    async def test_delete_not_found(self, db_session):
        repo = UserRepository(db_session)
        assert await repo.delete(999) is False


class TestSmartGroupRepositoryExtended:
    async def test_delete(self, db_session):
        repo = SmartGroupRepository(db_session)
        created = await repo.create({"name": "G", "created_by": 1})
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
        created = await repo.create({"name": "SG1", "created_by": 1})
        assert created.id is not None
        assert created.name == "SG1"

    async def test_list(self, db_session):
        repo = StaticGroupRepository(db_session)
        await repo.create({"name": "SG1", "created_by": 1})
        await repo.create({"name": "SG2", "created_by": 1})
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session):
        repo = StaticGroupRepository(db_session)
        for i in range(5):
            await repo.create({"name": f"SG{i}", "created_by": 1})
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create({"name": "SG1", "created_by": 1})
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "SG1"

    async def test_get_by_id_not_found(self, db_session):
        repo = StaticGroupRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create({"name": "SG1", "created_by": 1})
        updated = await repo.update(created.id, {"name": "SG2"})
        assert updated is not None
        assert updated.name == "SG2"

    async def test_update_not_found(self, db_session):
        repo = StaticGroupRepository(db_session)
        assert await repo.update(999, {"name": "x"}) is None

    async def test_delete(self, db_session):
        repo = StaticGroupRepository(db_session)
        created = await repo.create({"name": "SG1", "created_by": 1})
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = StaticGroupRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session):
        repo = StaticGroupRepository(db_session)
        assert await repo.count() == 0
        await repo.create({"name": "SG1", "created_by": 1})
        assert await repo.count() == 1

    async def test_get_device_serial_numbers(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        group = await repo.create({"name": "SG1", "created_by": 1})
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2])
        await db_session.commit()
        db_session.add(StaticGroupDevice(static_group_id=group.id, device_id=dev1.id))
        db_session.add(StaticGroupDevice(static_group_id=group.id, device_id=dev2.id))
        await db_session.commit()
        serials = await repo.get_device_serial_numbers(group.id)
        assert set(serials) == {"SN001", "SN002"}

    async def test_get_device_serial_numbers_empty(self, db_session):
        repo = StaticGroupRepository(db_session)
        group = await repo.create({"name": "SG1", "created_by": 1})
        serials = await repo.get_device_serial_numbers(group.id)
        assert serials == []

    async def test_set_device_serial_numbers(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        group = await repo.create({"name": "SG1", "created_by": 1})
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev3 = Device(name="D3", serial_number="SN003", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()
        await repo.set_device_serial_numbers(group.id, ["SN001", "SN002", "SN003"])
        serials = await repo.get_device_serial_numbers(group.id)
        assert set(serials) == {"SN001", "SN002", "SN003"}

    async def test_set_device_serial_numbers_replaces_existing(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        group = await repo.create({"name": "SG1", "created_by": 1})
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev2 = Device(name="D2", serial_number="SN002", os_version="14", connection_status="Online", enrollment_status="Compliant")
        dev3 = Device(name="D3", serial_number="SN003", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()
        await repo.set_device_serial_numbers(group.id, ["SN001", "SN002"])
        await repo.set_device_serial_numbers(group.id, ["SN003"])
        serials = await repo.get_device_serial_numbers(group.id)
        assert serials == ["SN003"]

    async def test_set_device_serial_numbers_empty_list(self, db_session):
        from app.devices.models import Device

        repo = StaticGroupRepository(db_session)
        group = await repo.create({"name": "SG1", "created_by": 1})
        dev1 = Device(name="D1", serial_number="SN001", os_version="14", connection_status="Online", enrollment_status="Compliant")
        db_session.add(dev1)
        await db_session.commit()
        await repo.set_device_serial_numbers(group.id, ["SN001"])
        await repo.set_device_serial_numbers(group.id, [])
        serials = await repo.get_device_serial_numbers(group.id)
        assert serials == []


class TestInventorySearchRepository:
    async def test_create(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create({"name": "search1", "created_by": 1})
        assert created.id is not None
        assert created.name == "search1"

    async def test_list(self, db_session):
        repo = InventorySearchRepository(db_session)
        await repo.create({"name": "s1", "created_by": 1})
        await repo.create({"name": "s2", "created_by": 1})
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session):
        repo = InventorySearchRepository(db_session)
        for i in range(5):
            await repo.create({"name": f"s{i}", "created_by": 1})
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create({"name": "s1", "created_by": 1})
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "s1"

    async def test_get_by_id_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create({"name": "s1", "created_by": 1})
        updated = await repo.update(created.id, {"name": "s2"})
        assert updated is not None
        assert updated.name == "s2"

    async def test_update_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.update(999, {"name": "x"}) is None

    async def test_delete(self, db_session):
        repo = InventorySearchRepository(db_session)
        created = await repo.create({"name": "s1", "created_by": 1})
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session):
        repo = InventorySearchRepository(db_session)
        assert await repo.count() == 0
        await repo.create({"name": "s1", "created_by": 1})
        assert await repo.count() == 1


class TestExtensionAttributeRepository:
    async def test_create(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create({"name": "ext1", "data_type": "string", "input_type": "Text field", "created_by": 1})
        assert created.id is not None
        assert created.name == "ext1"

    async def test_create_unique_name(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        data = {"name": "ext1", "data_type": "string", "input_type": "Text field", "created_by": 1}
        await repo.create(data)
        with pytest.raises(ConflictError):
            await repo.create(data)

    async def test_list(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        await repo.create({"name": "ext1", "data_type": "string", "input_type": "Text field", "created_by": 1})
        await repo.create({"name": "ext2", "data_type": "string", "input_type": "Text field", "created_by": 1})
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        for i in range(5):
            await repo.create({"name": f"ext{i}", "data_type": "string", "input_type": "Text field", "created_by": 1})
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create({"name": "ext1", "data_type": "string", "input_type": "Text field", "created_by": 1})
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "ext1"

    async def test_get_by_id_not_found(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_update(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create({"name": "ext1", "data_type": "string", "input_type": "Text field", "created_by": 1})
        updated = await repo.update(created.id, {"name": "ext2"})
        assert updated is not None
        assert updated.name == "ext2"

    async def test_update_not_found(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.update(999, {"name": "x"}) is None

    async def test_delete(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        created = await repo.create({"name": "ext1", "data_type": "string", "input_type": "Text field", "created_by": 1})
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.delete(999) is False

    async def test_count(self, db_session):
        repo = ExtensionAttributeRepository(db_session)
        assert await repo.count() == 0
        await repo.create({"name": "ext1", "data_type": "string", "input_type": "Text field", "created_by": 1})
        assert await repo.count() == 1
