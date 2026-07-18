import pytest
from app.core.exceptions import ConflictError
from app.devices.repositories import DeviceRepository
from app.devices.schemas import (
    Certificate,
    Cellular,
    DeviceUpdate,
    Network,
    Wifi,
)


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
            created.id,
            DeviceUpdate(connection_status="Offline"),
        )
        assert updated is not None
        assert updated.connection_status == "Offline"
        assert updated.serial_number == "SN001"

    async def test_update_not_found(self, db_session):
        repo = DeviceRepository(db_session)
        assert await repo.update(999, DeviceUpdate(connection_status="Offline")) is None

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
            DeviceUpdate(
                network=Network(
                    wifi=Wifi(ssid="Updated"), cellular=Cellular(carrier="Verizon")
                ),
            ),
        )
        assert updated.network.wifi.ssid == "Updated"
        assert updated.network.cellular.carrier == "Verizon"

    async def test_update_ext_attributes_replace(self, db_session):
        from app.extension_attributes.repositories import ExtensionAttributeRepository
        from app.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea1 = await ea_repo.create(
            ExtensionAttributeCreate(
                name="field1", data_type="string", input_type="Text field", created_by=1
            )
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())

        updated = await repo.update(
            device.id,
            DeviceUpdate(
                extension_attributes=[
                    {
                        "extension_attribute_id": ea1.id,
                        "extension_attribute_name": "field1",
                        "value": "val1",
                    },
                ],
            ),
        )
        assert len(updated.extension_attributes) == 1
        assert updated.extension_attributes[0].value == "val1"

    async def test_update_ext_attributes_clear(self, db_session):
        from app.extension_attributes.repositories import ExtensionAttributeRepository
        from app.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea1 = await ea_repo.create(
            ExtensionAttributeCreate(
                name="field1", data_type="string", input_type="Text field", created_by=1
            )
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        await repo.update(
            device.id,
            DeviceUpdate(
                extension_attributes=[
                    {
                        "extension_attribute_id": ea1.id,
                        "extension_attribute_name": "field1",
                        "value": "val1",
                    },
                ],
            ),
        )

        updated = await repo.update(
            device.id,
            DeviceUpdate(extension_attributes=[]),
        )
        assert updated.extension_attributes == []

    async def test_update_no_change(self, db_session):
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        updated = await repo.update(created.id, DeviceUpdate())
        assert updated is not None
        assert updated.serial_number == "SN001"

    async def test_update_certificates(self, db_session):
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        updated = await repo.update(
            created.id,
            DeviceUpdate(
                certificates=[
                    Certificate(common_name="new.com", issuer="CA2"),
                    Certificate(common_name="backup.com"),
                ],
            ),
        )
        assert len(updated.certificates) == 2
        assert updated.certificates[0].common_name == "new.com"
        assert updated.certificates[1].common_name == "backup.com"

    async def test_update_multiple_scalar_fields(self, db_session):
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        updated = await repo.update(
            created.id,
            DeviceUpdate(
                connection_status="Offline",
                enrollment_status="Non-compliant",
                battery_status=42,
                total_storage=512,
                available_storage=256,
            ),
        )
        assert updated.connection_status == "Offline"
        assert updated.enrollment_status == "Non-compliant"
        assert updated.battery_status == 42
        assert updated.total_storage == 512
        assert updated.available_storage == 256

    async def test_update_ext_attrs_and_scalar_together(self, db_session):
        from app.extension_attributes.repositories import ExtensionAttributeRepository
        from app.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea = await ea_repo.create(
            ExtensionAttributeCreate(
                name="field1", data_type="string", input_type="Text field", created_by=1
            )
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())

        updated = await repo.update(
            device.id,
            DeviceUpdate(
                battery_status=99,
                extension_attributes=[
                    {
                        "extension_attribute_id": ea.id,
                        "extension_attribute_name": "field1",
                        "value": "val1",
                    },
                ],
            ),
        )
        assert updated.battery_status == 99
        assert len(updated.extension_attributes) == 1
        assert updated.extension_attributes[0].value == "val1"

    async def test_update_ext_attrs_replace_multiple(self, db_session):
        from app.extension_attributes.repositories import ExtensionAttributeRepository
        from app.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea1 = await ea_repo.create(
            ExtensionAttributeCreate(
                name="field1", data_type="string", input_type="Text field", created_by=1
            )
        )
        ea2 = await ea_repo.create(
            ExtensionAttributeCreate(
                name="field2", data_type="integer", input_type="Text field", created_by=1
            )
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        await repo.update(
            device.id,
            DeviceUpdate(
                extension_attributes=[
                    {"extension_attribute_id": ea1.id, "extension_attribute_name": "field1", "value": "v1"},
                ],
            ),
        )

        updated = await repo.update(
            device.id,
            DeviceUpdate(
                extension_attributes=[
                    {"extension_attribute_id": ea2.id, "extension_attribute_name": "field2", "value": "v2"},
                    {"extension_attribute_id": ea1.id, "extension_attribute_name": "field1", "value": "v1-new"},
                ],
            ),
        )
        assert len(updated.extension_attributes) == 2
        values = {a.extension_attribute_name: a.value for a in updated.extension_attributes}
        assert values == {"field1": "v1-new", "field2": "v2"}
