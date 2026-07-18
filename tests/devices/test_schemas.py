from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.devices.schemas import (
    Certificate,
    Cellular,
    DeviceResponse,
    DeviceSearchCriteria,
    DeviceUpdate,
    Network,
    Wifi,
)

_DEVICE_FIELDS = {
    "id": 1,
    "serial_number": "SN001",
    "name": "Test",
    "os_version": "14.0",
    "connection_status": "Online",
    "enrollment_status": "Enrolled",
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "last_enrolled_at": datetime.now(timezone.utc),
}


class TestDeviceResponseSchema:
    def test_response_from_attributes(self) -> None:
        data = DeviceResponse(**_DEVICE_FIELDS)
        assert data.id == 1
        assert data.name == "Test"

    def test_optional_fields_default_to_none(self) -> None:
        data = DeviceResponse(**_DEVICE_FIELDS)
        assert data.battery_status is None
        assert data.network is None
        assert data.certificates is None

    def test_network_and_certificates_default_to_none(self) -> None:
        data = DeviceResponse(**_DEVICE_FIELDS)
        assert data.network is None
        assert data.certificates is None

    def test_with_network_info(self) -> None:
        wifi = Wifi(ssid="Office", bssid="00:11:22:33:44:55", signal_strength=-45)
        net = Network(wifi=wifi)
        data = DeviceResponse(**_DEVICE_FIELDS, network=net)
        assert data.network.wifi.ssid == "Office"
        assert data.network.wifi.bssid == "00:11:22:33:44:55"
        assert data.network.wifi.signal_strength == -45
        assert data.network.cellular is None

    def test_with_network_cellular(self) -> None:
        cell = Cellular(carrier="AT&T", imei="123456789012345", roaming=False)
        net = Network(cellular=cell)
        data = DeviceResponse(**_DEVICE_FIELDS, network=net)
        assert data.network.cellular.carrier == "AT&T"
        assert data.network.cellular.imei == "123456789012345"
        assert data.network.cellular.roaming is False
        assert data.network.wifi is None

    def test_with_certificates(self) -> None:
        certs = [
            Certificate(common_name="example.com", issuer="CA Inc", type="identity"),
            Certificate(common_name="backup.example.com", fingerprint="AB:CD:EF"),
        ]
        data = DeviceResponse(**_DEVICE_FIELDS, certificates=certs)
        assert len(data.certificates) == 2
        assert data.certificates[0].common_name == "example.com"
        assert data.certificates[0].type == "identity"
        assert data.certificates[1].fingerprint == "AB:CD:EF"


class TestDeviceSearchCriteriaSchema:
    def test_search_criteria_valid(self) -> None:
        data = DeviceSearchCriteria(
            criteria=[{"field": "status", "operator": "is", "value": "Online"}]
        )
        assert len(data.criteria) == 1
        assert data.criteria[0]["field"] == "status"

    def test_search_criteria_empty(self) -> None:
        data = DeviceSearchCriteria(criteria=[])
        assert data.criteria == []


class TestWifiSchema:
    def test_all_fields_default_to_none(self) -> None:
        w = Wifi()
        assert w.ssid is None
        assert w.bssid is None
        assert w.ip_address is None
        assert w.gateway is None
        assert w.dns is None
        assert w.mac_address is None
        assert w.proxy is None
        assert w.signal_strength is None

    def test_constructor(self) -> None:
        w = Wifi(ssid="Home", mac_address="aa:bb:cc:dd:ee:ff", signal_strength=-60)
        assert w.ssid == "Home"
        assert w.mac_address == "aa:bb:cc:dd:ee:ff"
        assert w.signal_strength == -60


class TestCellularSchema:
    def test_all_fields_default_to_none(self) -> None:
        c = Cellular()
        assert c.carrier is None
        assert c.ip_address is None
        assert c.imei is None
        assert c.roaming is None

    def test_constructor(self) -> None:
        c = Cellular(carrier="Verizon", connection_type="5G", roaming=True)
        assert c.carrier == "Verizon"
        assert c.connection_type == "5G"
        assert c.roaming is True


class TestNetworkSchema:
    def test_both_subfields_default_to_none(self) -> None:
        n = Network()
        assert n.wifi is None
        assert n.cellular is None

    def test_with_wifi(self) -> None:
        n = Network(wifi=Wifi(ssid="Guest"))
        assert n.wifi.ssid == "Guest"
        assert n.cellular is None

    def test_with_cellular(self) -> None:
        n = Network(cellular=Cellular(imei="000000000000000"))
        assert n.cellular.imei == "000000000000000"
        assert n.wifi is None

    def test_model_dump_roundtrip(self) -> None:
        n = Network(wifi=Wifi(ssid="Test"), cellular=Cellular(carrier="T-Mobile"))
        dumped = n.model_dump()
        loaded = Network.model_validate(dumped)
        assert loaded.wifi.ssid == "Test"
        assert loaded.cellular.carrier == "T-Mobile"


class TestCertificateSchema:
    def test_all_fields_default_to_none(self) -> None:
        c = Certificate()
        assert c.common_name is None
        assert c.issuer is None
        assert c.expiry is None
        assert c.type is None
        assert c.fingerprint is None
        assert c.serial_number is None

    def test_constructor(self) -> None:
        c = Certificate(common_name="example.com", issuer="CA Inc", type="identity")
        assert c.common_name == "example.com"
        assert c.issuer == "CA Inc"
        assert c.type == "identity"

    def test_model_dump_roundtrip(self) -> None:
        c = Certificate(common_name="test.com", fingerprint="12:34:56")
        dumped = c.model_dump()
        loaded = Certificate.model_validate(dumped)
        assert loaded.common_name == "test.com"
        assert loaded.fingerprint == "12:34:56"


class TestDeviceUpdateSchema:
    def test_update_all_fields(self) -> None:
        data = DeviceUpdate(
            connection_status="Offline",
            enrollment_status="Non-compliant",
            battery_status=50,
            total_storage=256,
            available_storage=128,
            total_memory=16,
            available_memory=8,
            network=Network(wifi=Wifi(ssid="Home")),
            certificates=[Certificate(common_name="test.com")],
            extension_attributes=[
                {
                    "extension_attribute_id": 1,
                    "extension_attribute_name": "custom_field",
                    "value": "test_value",
                },
            ],
        )
        assert data.connection_status == "Offline"
        assert data.enrollment_status == "Non-compliant"
        assert data.battery_status == 50
        assert data.network.wifi.ssid == "Home"
        assert len(data.certificates) == 1
        assert len(data.extension_attributes) == 1

    def test_update_partial(self) -> None:
        data = DeviceUpdate(connection_status="Online")
        dumped = data.model_dump(exclude_unset=True)
        assert dumped == {"connection_status": "Online"}

    def test_update_empty(self) -> None:
        data = DeviceUpdate()
        assert data.model_dump(exclude_unset=True) == {}

    def test_update_ext_attrs_optional(self) -> None:
        data = DeviceUpdate()
        assert data.extension_attributes is None

    def test_update_ext_attrs_empty_list(self) -> None:
        data = DeviceUpdate(extension_attributes=[])
        assert data.extension_attributes == []

    def test_update_ext_attrs_missing_name(self) -> None:
        with pytest.raises(ValidationError):
            DeviceUpdate(
                extension_attributes=[{"extension_attribute_id": 1, "value": "test"}]
            )

    def test_update_invalid_connection_status(self) -> None:
        with pytest.raises(ValidationError):
            DeviceUpdate(connection_status="INVALID")

    def test_update_invalid_enrollment_status(self) -> None:
        with pytest.raises(ValidationError):
            DeviceUpdate(enrollment_status="INVALID")
