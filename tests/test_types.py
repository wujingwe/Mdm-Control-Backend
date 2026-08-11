from sqlalchemy.dialects import sqlite

from app.infra.core.types import CertificateListType, NetworkInfoType
from app.domains.devices.schemas import Certificate, Network, Wifi

dialect = sqlite.dialect()


class TestNetworkInfoType:
    def test_bind_none(self) -> None:
        t = NetworkInfoType()
        assert t.process_bind_param(None, dialect) is None

    def test_bind_network_info_object(self) -> None:
        t = NetworkInfoType()
        net = Network(wifi=Wifi(ssid="Home"))
        result = t.process_bind_param(net, dialect)
        assert result is not None
        assert result["wifi"]["ssid"] == "Home"
        assert result["cellular"] is None

    def test_result_none(self) -> None:
        t = NetworkInfoType()
        assert t.process_result_value(None, dialect) is None

    def test_result_valid_dict(self) -> None:
        t = NetworkInfoType()
        result = t.process_result_value({"wifi": {"ssid": "Home"}}, dialect)
        assert isinstance(result, Network)
        assert result.wifi is not None
        assert result.wifi.ssid == "Home"
        assert result.cellular is None

    def test_result_with_cellular(self) -> None:
        t = NetworkInfoType()
        result = t.process_result_value(
            {"wifi": None, "cellular": {"carrier": "AT&T", "roaming": False}},
            dialect,
        )
        assert isinstance(result, Network)
        assert result.cellular is not None
        assert result.cellular.carrier == "AT&T"
        assert result.cellular.roaming is False


class TestCertificateListType:
    def test_bind_none(self) -> None:
        t = CertificateListType()
        assert t.process_bind_param(None, dialect) is None

    def test_bind_certificate_info_list(self) -> None:
        t = CertificateListType()
        certs = [Certificate(common_name="a.com"), Certificate(common_name="b.com")]
        result = t.process_bind_param(certs, dialect)
        assert result is not None
        assert len(result) == 2
        assert result[0]["common_name"] == "a.com"
        assert result[1]["common_name"] == "b.com"

    def test_result_none(self) -> None:
        t = CertificateListType()
        assert t.process_result_value(None, dialect) is None

    def test_result_valid_list(self) -> None:
        t = CertificateListType()
        result = t.process_result_value([{"common_name": "a.com"}, {"common_name": "b.com"}], dialect)
        assert result is not None
        assert len(result) == 2
        assert isinstance(result[0], Certificate)
        assert result[0].common_name == "a.com"
        assert result[1].common_name == "b.com"
