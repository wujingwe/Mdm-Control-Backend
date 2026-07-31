import pytest
from app.infra.core.exceptions import ConflictError
from app.domains.devices.repositories import DeviceRepository
from app.domains.devices.schemas import (
    Certificate,
    Cellular,
    DeviceResponse,
    DeviceUpdate,
    Network,
    Wifi,
)
from sqlalchemy.ext.asyncio import AsyncSession


def _make_device_data(serial: str = "SN001", name: str = "Test Device") -> dict:
    return {
        "name": name,
        "serial_number": serial,
        "os_version": "14.0",
        "connection_status": "Connected",
        "status": "Enrolled",
    }


class TestDeviceRepository:
    async def test_create(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        assert device.id is not None
        assert device.serial_number == "SN001"
        assert device.name == "Test Device"

    async def test_create_all_fields(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        data = _make_device_data()
        data["battery_status"] = 85
        data["total_storage"] = 512
        data["available_storage"] = 256
        data["total_memory"] = 16
        data["available_memory"] = 8
        data["network"] = Network(wifi=Wifi(ssid="Office"))
        data["certificates"] = [Certificate(common_name="example.com")]
        device = await repo.create(data)
        assert device.battery_status == 85
        assert device.total_storage == 512
        assert device.available_storage == 256
        assert device.total_memory == 16
        assert device.available_memory == 8
        assert device.network.wifi.ssid == "Office"
        assert len(device.certificates) == 1

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.serial_number == "SN001"

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_get_by_id_loads_extension_attributes(self, db_session: AsyncSession) -> None:
        from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
        from app.domains.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea = await ea_repo.create(
            ExtensionAttributeCreate(name="field1", data_type="string", input_type="Text field"),
            created_by=1,
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        await repo.update(
            device.id,
            DeviceUpdate(
                extension_attribute_values=[
                    {
                        "extension_attribute_id": ea.id,
                        "extension_attribute_name": "field1",
                        "value": "v1",
                    },
                ],
            ),
        )

        found = await repo.get_by_id(device.id)
        assert found is not None
        assert len(found.extension_attribute_values) == 1
        assert found.extension_attribute_values[0].value == "v1"

    async def test_get_by_id_loads_latest_profiles(self, db_session: AsyncSession) -> None:
        from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
        from app.domains.profiles.repositories import ProfileRepository
        from app.domains.profiles.schemas.profile import AssignmentUpsert, ProfileCreate
        from app.domains.profiles.schemas.policy import Policy
        from app.domains.shared.scope import Scope

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        profile_repo = ProfileRepository(db_session)

        present = await profile_repo.create(
            ProfileCreate(name="Present", policy=Policy(), scope=Scope()),
            created_by=1,
        )
        revoked = await profile_repo.create(
            ProfileCreate(name="Revoked", policy=Policy(), scope=Scope()),
            created_by=1,
        )
        await profile_repo.create(
            ProfileCreate(name="NeverAssigned", policy=Policy(), scope=Scope()),
            created_by=1,
        )

        await profile_repo.upsert_assignment(
            AssignmentUpsert(
                profile_id=present.id,
                device_id=device.id,
                status=AssignmentStatus.PENDING,
                desired_state=AssignmentDesiredState.PRESENT,
                profile_version=1,
            )
        )
        await profile_repo.upsert_assignment(
            AssignmentUpsert(
                profile_id=revoked.id,
                device_id=device.id,
                status=AssignmentStatus.PENDING,
                desired_state=AssignmentDesiredState.ABSENT,
                profile_version=2,
            )
        )

        found = await repo.get_by_id(device.id)
        assert found is not None
        assert {p.id for p in found.profiles} == {present.id, revoked.id}

        resp = DeviceResponse.model_validate(found)
        assert resp.profiles is not None
        assert {p.id for p in resp.profiles} == {present.id, revoked.id}
        assert resp.mobile_apps == []

    async def test_get_by_id_loads_latest_mobile_apps(self, db_session: AsyncSession) -> None:
        from app.domains.mobile_apps.repositories import MobileAppRepository
        from app.domains.mobile_apps.schemas import MobileAppAssignmentUpsert, MobileAppCreate
        from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
        from app.domains.shared.scope import Scope

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        app_repo = MobileAppRepository(db_session)

        present = await app_repo.create(
            MobileAppCreate(
                name="AppPresent",
                enabled=True,
                package_version="1.0",
                package_name="com.app.present",
                scope=Scope(),
            ),
            created_by=1,
        )
        revoked = await app_repo.create(
            MobileAppCreate(
                name="AppRevoked",
                enabled=True,
                package_version="1.0",
                package_name="com.app.revoked",
                scope=Scope(),
            ),
            created_by=1,
        )
        await app_repo.create(
            MobileAppCreate(
                name="AppNeverAssigned",
                enabled=True,
                package_version="1.0",
                package_name="com.app.never",
                scope=Scope(),
            ),
            created_by=1,
        )

        await app_repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=present.id,
                device_id=device.id,
                status=AssignmentStatus.PENDING,
                desired_state=AssignmentDesiredState.PRESENT,
                version=1,
            )
        )
        await app_repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=revoked.id,
                device_id=device.id,
                status=AssignmentStatus.PENDING,
                desired_state=AssignmentDesiredState.ABSENT,
                version=2,
            )
        )

        found = await repo.get_by_id(device.id)
        assert found is not None
        assert {a.id for a in found.mobile_apps} == {present.id, revoked.id}

        resp = DeviceResponse.model_validate(found)
        assert resp.mobile_apps is not None
        assert {a.id for a in resp.mobile_apps} == {present.id, revoked.id}
        assert resp.profiles == []

    async def test_list(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        await repo.create(_make_device_data(serial="SN001"))
        await repo.create(_make_device_data(serial="SN002"))
        await repo.create(_make_device_data(serial="SN003"))
        items = await repo.list()
        assert len(items) == 3

    async def test_response_relationship_fields_empty_without_eager_load(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        item = (await repo.list())[0]
        assert item.id == device.id
        resp = DeviceResponse.model_validate(item)
        assert resp.extension_attribute_values == []
        assert resp.profiles == []
        assert resp.mobile_apps == []

    async def test_list_pagination(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        for i in range(5):
            await repo.create(_make_device_data(serial=f"SN{i:03d}"))
        page1 = await repo.list(skip=0, limit=2)
        assert len(page1) == 2
        page2 = await repo.list(skip=2, limit=2)
        assert len(page2) == 2
        page3 = await repo.list(skip=4, limit=2)
        assert len(page3) == 1

    async def test_list_empty(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        items = await repo.list()
        assert items == []

    async def test_update(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert (
            await repo.update(
                created.id,
                DeviceUpdate(connection_status="Disconnected"),
            )
            == 1
        )
        updated = await repo.get_by_id(created.id)
        assert updated is not None
        assert updated.connection_status == "Disconnected"
        assert updated.serial_number == "SN001"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        assert await repo.update(999, DeviceUpdate(connection_status="Disconnected")) == 0

    async def test_update_network(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert (
            await repo.update(
                created.id,
                DeviceUpdate(
                    network=Network(wifi=Wifi(ssid="Updated"), cellular=Cellular(carrier="Verizon")),
                ),
            )
            == 1
        )
        updated = await repo.get_by_id(created.id)
        assert updated is not None
        assert updated.network.wifi.ssid == "Updated"
        assert updated.network.cellular.carrier == "Verizon"

    async def test_update_clear_network(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create({**_make_device_data(), "network": Network(wifi=Wifi(ssid="Office"))})
        assert created.network is not None

        assert await repo.update(created.id, DeviceUpdate(network=None)) == 1
        updated = await repo.get_by_id(created.id)
        assert updated is not None
        assert updated.network is None

    async def test_update_certificates(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert (
            await repo.update(
                created.id,
                DeviceUpdate(
                    certificates=[
                        Certificate(common_name="new.com", issuer="CA2"),
                        Certificate(common_name="backup.com"),
                    ],
                ),
            )
            == 1
        )
        updated = await repo.get_by_id(created.id)
        assert updated is not None
        assert len(updated.certificates) == 2
        assert updated.certificates[0].common_name == "new.com"
        assert updated.certificates[1].common_name == "backup.com"

    async def test_update_clear_certificates(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(
            {
                **_make_device_data(),
                "certificates": [Certificate(common_name="old.com")],
            }
        )
        assert len(created.certificates) == 1

        assert await repo.update(created.id, DeviceUpdate(certificates=None)) == 1
        updated = await repo.get_by_id(created.id)
        assert updated is not None
        assert updated.certificates is None

    async def test_update_multiple_scalar_fields(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert (
            await repo.update(
                created.id,
                DeviceUpdate(
                    connection_status="Disconnected",
                    status="Unenrolled",
                    battery_status=42,
                    total_storage=512,
                    available_storage=256,
                ),
            )
            == 1
        )
        updated = await repo.get_by_id(created.id)
        assert updated is not None
        assert updated.connection_status == "Disconnected"
        assert updated.status == "Unenrolled"
        assert updated.battery_status == 42
        assert updated.total_storage == 512
        assert updated.available_storage == 256

    async def test_update_ext_attributes_replace(self, db_session: AsyncSession) -> None:
        from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
        from app.domains.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea1 = await ea_repo.create(
            ExtensionAttributeCreate(name="field1", data_type="string", input_type="Text field"),
            created_by=1,
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())

        assert (
            await repo.update(
                device.id,
                DeviceUpdate(
                    extension_attribute_values=[
                        {
                            "extension_attribute_id": ea1.id,
                            "extension_attribute_name": "field1",
                            "value": "val1",
                        },
                    ],
                ),
            )
            == 1
        )
        updated = await repo.get_by_id(device.id)
        assert updated is not None
        assert len(updated.extension_attribute_values) == 1
        assert updated.extension_attribute_values[0].value == "val1"

    async def test_update_ext_attributes_clear(self, db_session: AsyncSession) -> None:
        from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
        from app.domains.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea1 = await ea_repo.create(
            ExtensionAttributeCreate(name="field1", data_type="string", input_type="Text field"),
            created_by=1,
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        await repo.update(
            device.id,
            DeviceUpdate(
                extension_attribute_values=[
                    {
                        "extension_attribute_id": ea1.id,
                        "extension_attribute_name": "field1",
                        "value": "val1",
                    },
                ],
            ),
        )

        assert (
            await repo.update(
                device.id,
                DeviceUpdate(extension_attribute_values=[]),
            )
            == 1
        )
        updated = await repo.get_by_id(device.id)
        assert updated is not None
        assert updated.extension_attribute_values == []

    async def test_update_ext_attrs_and_scalar_together(self, db_session: AsyncSession) -> None:
        from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
        from app.domains.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea = await ea_repo.create(
            ExtensionAttributeCreate(name="field1", data_type="string", input_type="Text field"),
            created_by=1,
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())

        assert (
            await repo.update(
                device.id,
                DeviceUpdate(
                    battery_status=99,
                    extension_attribute_values=[
                        {
                            "extension_attribute_id": ea.id,
                            "extension_attribute_name": "field1",
                            "value": "val1",
                        },
                    ],
                ),
            )
            == 1
        )
        updated = await repo.get_by_id(device.id)
        assert updated is not None
        assert updated.battery_status == 99
        assert len(updated.extension_attribute_values) == 1
        assert updated.extension_attribute_values[0].value == "val1"

    async def test_update_ext_attrs_replace_multiple(self, db_session: AsyncSession) -> None:
        from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
        from app.domains.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea1 = await ea_repo.create(
            ExtensionAttributeCreate(name="field1", data_type="string", input_type="Text field"),
            created_by=1,
        )
        ea2 = await ea_repo.create(
            ExtensionAttributeCreate(
                name="field2",
                data_type="integer",
                input_type="Text field",
            ),
            created_by=1,
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        await repo.update(
            device.id,
            DeviceUpdate(
                extension_attribute_values=[
                    {
                        "extension_attribute_id": ea1.id,
                        "extension_attribute_name": "field1",
                        "value": "v1",
                    },
                ],
            ),
        )

        assert (
            await repo.update(
                device.id,
                DeviceUpdate(
                    extension_attribute_values=[
                        {
                            "extension_attribute_id": ea2.id,
                            "extension_attribute_name": "field2",
                            "value": "v2",
                        },
                        {
                            "extension_attribute_id": ea1.id,
                            "extension_attribute_name": "field1",
                            "value": "v1-new",
                        },
                    ],
                ),
            )
            == 1
        )
        updated = await repo.get_by_id(device.id)
        assert updated is not None
        assert len(updated.extension_attribute_values) == 2
        values = {a.extension_attribute_name: a.value for a in updated.extension_attribute_values}
        assert values == {"field1": "v1-new", "field2": "v2"}

    async def test_update_no_change(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert await repo.update(created.id, DeviceUpdate()) == 0

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert await repo.delete(created.id) == 1
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        assert await repo.delete(999) == 0

    async def test_delete_removes_device(self, db_session: AsyncSession) -> None:
        from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
        from app.domains.extension_attributes.schemas import ExtensionAttributeCreate

        ea_repo = ExtensionAttributeRepository(db_session)
        ea = await ea_repo.create(
            ExtensionAttributeCreate(name="field1", data_type="string", input_type="Text field"),
            created_by=1,
        )

        repo = DeviceRepository(db_session)
        device = await repo.create(_make_device_data())
        await repo.update(
            device.id,
            DeviceUpdate(
                extension_attribute_values=[
                    {
                        "extension_attribute_id": ea.id,
                        "extension_attribute_name": "field1",
                        "value": "v1",
                    },
                ],
            ),
        )

        assert await repo.get_by_id(device.id) is not None
        assert await repo.delete(device.id) == 1
        assert await repo.get_by_id(device.id) is None

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        assert await repo.count() == 0
        await repo.create(_make_device_data())
        assert await repo.count() == 1

    async def test_count_after_delete(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        d1 = await repo.create(_make_device_data(serial="SN001"))
        await repo.create(_make_device_data(serial="SN002"))
        assert await repo.count() == 2
        await repo.delete(d1.id)
        assert await repo.count() == 1

    async def test_unique_serial(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        await repo.create(_make_device_data())
        with pytest.raises(ConflictError):
            await repo.create(_make_device_data())

    async def test_create_with_network_and_certificates(self, db_session: AsyncSession) -> None:
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

    async def test_update_with_network_wifi_only(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert await repo.update(created.id, DeviceUpdate(network=Network(wifi=Wifi(ssid="NewWifi")))) == 1
        updated = await repo.get_by_id(created.id)
        assert updated is not None
        assert updated.network.wifi.ssid == "NewWifi"
        assert updated.network.cellular is None

    async def test_update_with_network_cellular_only(self, db_session: AsyncSession) -> None:
        repo = DeviceRepository(db_session)
        created = await repo.create(_make_device_data())
        assert (
            await repo.update(
                created.id, DeviceUpdate(network=Network(cellular=Cellular(carrier="T-Mobile", roaming=True)))
            )
            == 1
        )
        updated = await repo.get_by_id(created.id)
        assert updated is not None
        assert updated.network.cellular.carrier == "T-Mobile"
        assert updated.network.cellular.roaming is True
        assert updated.network.wifi is None
