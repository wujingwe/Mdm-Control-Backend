import pytest
from app.core.exceptions import ConflictError
from app.devices.repositories import DeviceRepository
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
        updated = await repo.update(
            created.id, {"name": "New", "connection_status": "Offline"}
        )
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
        updated = await repo.update(
            created.id,
            {
                "network": Network(
                    wifi=Wifi(ssid="Updated"), cellular=Cellular(carrier="Verizon")
                ),
            },
        )
        assert updated.network.wifi.ssid == "Updated"
        assert updated.network.cellular.carrier == "Verizon"
