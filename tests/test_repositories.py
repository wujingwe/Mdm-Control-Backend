import pytest
from app.core.exceptions import ConflictError
from app.repositories.device import DeviceRepository
from app.repositories.policy import PolicyRepository
from app.repositories.smart_group import SmartGroupRepository
from app.repositories.user import UserRepository
from app.schemas.device import Certificate, Cellular, Network, Wifi


def _make_device_data(serial: str = "SN001", name: str = "Test Device") -> dict:
    return {
        "name": name,
        "serial_number": serial,
        "os_version": "14.0",
        "connection_status": "Online",
        "enrollment_status": "Enrolled",
    }


def _make_policy_data(name: str = "Policy A") -> dict:
    return {
        "name": name,
        "version": 1,
        "scope": "all",
        "rollout_state": "Completed",
        "target_devices": 0,
        "applied_devices": 0,
    }


class TestDeviceRepository:
    async def test_list_empty(self, db_session):
        repo = DeviceRepository(db_session)
        assert await repo.list_all_simple() == []

    async def test_create(self, db_session):
        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        assert device.id is not None
        assert device.serial_number == "SN001"
        assert device.name == "Test Device"

    async def test_list(self, db_session):
        repo = DeviceRepository(db_session)
        await repo.create(_make_device_data("SN001", "D1"))
        await repo.create(_make_device_data("SN002", "D2"))
        items = await repo.list_all_simple()
        assert len(items) == 2

    async def test_list_with_pagination(self, db_session):
        repo = DeviceRepository(db_session)
        for i in range(5):
            await repo.create(_make_device_data(f"SN{i:03d}", f"D{i}"))
        items = await repo.list_all_simple(skip=2, limit=2)
        assert len(items) == 2

    async def test_get_by_id(self, db_session):
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.serial_number == "SN001"

    async def test_get_by_id_not_found(self, db_session):
        repo = DeviceRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_get_by_serial(self, db_session):
        repo = DeviceRepository(db_session)
        await repo.create(_make_device_data())
        found = await repo.get_by_serial("SN001")
        assert found is not None
        assert found.name == "Test Device"

    async def test_get_by_serial_not_found(self, db_session):
        repo = DeviceRepository(db_session)
        assert await repo.get_by_serial("NONEXIST") is None

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


class TestPolicyRepository:
    async def test_crud(self, db_session):
        repo = PolicyRepository(db_session)
        created = await repo.create(_make_policy_data())
        assert created.id is not None
        assert created.name == "Policy A"

        found = await repo.get_by_id(created.id)
        assert found is not None

        updated = await repo.update(created.id, {"description": "new desc"})
        assert updated.description == "new desc"

        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_list(self, db_session):
        repo = PolicyRepository(db_session)
        await repo.create(_make_policy_data("P1"))
        await repo.create(_make_policy_data("P2"))
        assert len(await repo.list_all()) == 2


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
