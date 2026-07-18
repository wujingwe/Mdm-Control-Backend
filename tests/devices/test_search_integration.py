import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ConnectionStatus
from app.devices.models import Device
from app.devices.repositories import DeviceRepository
from app.devices.schemas import DeviceSearchCriteria
from app.devices.services import DeviceService
from collections.abc import Callable, Coroutine


@pytest.fixture
async def devices(db_session: AsyncSession) -> tuple[DeviceService, dict[str, Device]]:
    """Create 6 devices with diverse attributes for filtering tests."""
    devs = [
        Device(
            name="MacBook Pro",
            serial_number="SN-MBP-001",
            os_version="macOS 15.0",
            connection_status="Online",
            enrollment_status="Enrolled",
            battery_status=95,
            total_storage=1000,
            available_storage=500,
        ),
        Device(
            name="MacBook Air",
            serial_number="SN-MBA-002",
            os_version="macOS 14.5",
            connection_status="Online",
            enrollment_status="Enrolled",
            battery_status=30,
            total_storage=512,
            available_storage=200,
        ),
        Device(
            name="iPhone 15",
            serial_number="SN-IP15-003",
            os_version="iOS 18.1",
            connection_status="Offline",
            enrollment_status="Enrolled",
            battery_status=10,
            total_storage=256,
            available_storage=100,
        ),
        Device(
            name="iPhone SE",
            serial_number="SN-IPSE-004",
            os_version="iOS 17.4",
            connection_status=ConnectionStatus.ONLINE,
            enrollment_status="Pending",
            battery_status=80,
            total_storage=128,
            available_storage=64,
        ),
        Device(
            name="Galaxy S24",
            serial_number="SN-GS24-005",
            os_version="Android 14",
            connection_status="Offline",
            enrollment_status="Unknown",
            battery_status=50,
            total_storage=256,
            available_storage=256,
        ),
        Device(
            name="Pixel 8",
            serial_number="SN-PIX-006",
            os_version="Android 15",
            connection_status="Online",
            enrollment_status="Enrolled",
            battery_status=None,
            total_storage=128,
            available_storage=None,
        ),
    ]
    db_session.add_all(devs)
    await db_session.commit()
    repo = DeviceRepository(db_session)
    return DeviceService(repo), {d.serial_number: d for d in devs}




SearchFn = Callable[[DeviceService, str, str, str, str], Coroutine[None, None, list[Device]]]


@pytest.fixture
def search() -> SearchFn:
    """Helper to build DeviceSearchCriteria from shorthand."""

    async def _search(service: DeviceService, field: str, operator: str, value: str, conjunction: str = "AND") -> list[Device]:
        return await service.search_devices(
            DeviceSearchCriteria(
                conjunction=conjunction,
                criteria=[{"field": field, "operator": operator, "value": value}],
            )
        )

    return _search


def _names(result: list[Device]) -> list[str]:
    """Extract names from search result, sorted case-insensitively."""
    return sorted((d.name for d in result), key=str.casefold)


def _serials(result: list[Device]) -> list[str]:
    """Extract serial_numbers from search result."""
    return sorted(d.serial_number for d in result)


class TestSearchIsOperator:
    async def test_is_online(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "connection_status", "is", "Online")
        assert _names(result) == ["iPhone SE", "MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_is_offline(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "connection_status", "is", "Offline")
        assert _names(result) == ["Galaxy S24", "iPhone 15"]

    async def test_is_enrolled(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "enrollment_status", "is", "Enrolled")
        assert _names(result) == ["iPhone 15", "MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_is_exact_name(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "name", "is", "iPhone 15")
        assert len(result) == 1
        assert result[0].name == "iPhone 15"


class TestSearchIsNotOperator:
    async def test_is_not_offline(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "connection_status", "isNot", "Offline")
        assert _names(result) == ["iPhone SE", "MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_is_not_enrolled(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "enrollment_status", "isNot", "Enrolled")
        assert _names(result) == ["Galaxy S24", "iPhone SE"]


class TestSearchLikeOperator:
    async def test_like_mac(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "name", "like", "Mac")
        assert _names(result) == ["MacBook Air", "MacBook Pro"]

    async def test_like_iphone(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "name", "like", "iPhone")
        assert _names(result) == ["iPhone 15", "iPhone SE"]

    async def test_like_os_version_android(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "os_version", "like", "Android")
        assert _names(result) == ["Galaxy S24", "Pixel 8"]


class TestSearchNotLikeOperator:
    async def test_not_like_mac(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "name", "notLike", "Mac")
        assert _names(result) == ["Galaxy S24", "iPhone 15", "iPhone SE", "Pixel 8"]

    async def test_not_like_ios(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "os_version", "notLike", "iOS")
        assert _names(result) == ["Galaxy S24", "MacBook Air", "MacBook Pro", "Pixel 8"]


class TestSearchGreaterThanOperator:
    async def test_greater_than_80_battery(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "greaterThan", "80")
        assert _names(result) == ["MacBook Pro"]

    async def test_greater_than_50_battery(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "greaterThan", "50")
        assert _names(result) == ["iPhone SE", "MacBook Pro"]

    async def test_greater_than_excludes_none(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "greaterThan", "0")
        assert _names(result) == [
            "Galaxy S24",
            "iPhone 15",
            "iPhone SE",
            "MacBook Air",
            "MacBook Pro",
        ]


class TestSearchLessThanOperator:
    async def test_less_than_30_battery(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "lessThan", "30")
        assert _names(result) == ["iPhone 15"]

    async def test_less_than_50_battery(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "lessThan", "50")
        assert _names(result) == ["iPhone 15", "MacBook Air"]


class TestSearchGreaterThanOrEqualOperator:
    async def test_gte_80(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "greaterThanOrEqual", "80")
        assert _names(result) == ["iPhone SE", "MacBook Pro"]

    async def test_gte_50(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "greaterThanOrEqual", "50")
        assert _names(result) == ["Galaxy S24", "iPhone SE", "MacBook Pro"]


class TestSearchLessThanOrEqualOperator:
    async def test_lte_30(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "lessThanOrEqual", "30")
        assert _names(result) == ["iPhone 15", "MacBook Air"]

    async def test_lte_50(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "lessThanOrEqual", "50")
        assert _names(result) == ["Galaxy S24", "iPhone 15", "MacBook Air"]


class TestSearchRegexOperator:
    async def test_matches_regex(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "os_version", "matchesRegex", "^macOS")
        assert _names(result) == ["MacBook Air", "MacBook Pro"]

    async def test_does_not_match_regex(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "os_version", "doesNotMatchRegex", "^macOS")
        assert _names(result) == ["Galaxy S24", "iPhone 15", "iPhone SE", "Pixel 8"]

    async def test_regex_partial_match(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "name", "matchesRegex", "^.*\\s(Pro|Air)$")
        assert _names(result) == ["MacBook Air", "MacBook Pro"]


class TestSearchConjunctions:
    async def test_and_online_enrolled(self, devices: tuple[DeviceService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.search_devices(
            DeviceSearchCriteria(
                conjunction="AND",
                criteria=[
                    {"field": "connection_status", "operator": "is", "value": "Online"},
                    {"field": "enrollment_status", "operator": "is", "value": "Enrolled"},
                ],
            )
        )
        assert _names(result) == ["MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_or_online_or_enrolled(self, devices: tuple[DeviceService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.search_devices(
            DeviceSearchCriteria(
                conjunction="OR",
                criteria=[
                    {"field": "name", "operator": "like", "value": "Mac"},
                    {"field": "name", "operator": "like", "value": "iPhone"},
                ],
            )
        )
        assert _names(result) == [
            "iPhone 15",
            "iPhone SE",
            "MacBook Air",
            "MacBook Pro",
        ]

    async def test_and_no_match(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "connection_status", "is", "Online")
        online = _names(result)
        result2 = await search(svc, "enrollment_status", "is", "Needs attention")
        needs_attention = _names(result2)
        assert len(set(online) & set(needs_attention)) == 0


class TestSearchMultiCriteria:
    async def test_three_criteria_and(self, devices: tuple[DeviceService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.search_devices(
            DeviceSearchCriteria(
                conjunction="AND",
                criteria=[
                    {"field": "os_version", "operator": "like", "value": "iOS"},
                    {"field": "enrollment_status", "operator": "is", "value": "Enrolled"},
                    {"field": "battery_status", "operator": "greaterThan", "value": "5"},
                ],
            )
        )
        assert _names(result) == ["iPhone 15"]

    async def test_two_criteria_or(self, devices: tuple[DeviceService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.search_devices(
            DeviceSearchCriteria(
                conjunction="OR",
                criteria=[
                    {"field": "os_version", "operator": "is", "value": "macOS 15.0"},
                    {"field": "os_version", "operator": "is", "value": "Android 15"},
                ],
            )
        )
        assert _names(result) == ["MacBook Pro", "Pixel 8"]

    async def test_criteria_across_different_fields(self, devices: tuple[DeviceService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.search_devices(
            DeviceSearchCriteria(
                conjunction="AND",
                criteria=[
                    {"field": "connection_status", "operator": "is", "value": "Online"},
                    {"field": "enrollment_status", "operator": "isNot", "value": "Pending"},
                    {"field": "name", "operator": "notLike", "value": "Pixel"},
                ],
            )
        )
        assert _names(result) == ["MacBook Air", "MacBook Pro"]


class TestSearchEdgeCases:
    async def test_no_match_returns_empty(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "name", "is", "NonExistent Device")
        assert result == []

    async def test_unknown_field_returns_all(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "nonexistent_field", "is", "value")
        assert len(result) == 6

    async def test_empty_criteria_returns_all(self, devices: tuple[DeviceService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.search_devices(DeviceSearchCriteria(criteria=[]))
        assert len(result) == 6

    async def test_battery_status_none_excluded_from_numeric(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "battery_status", "greaterThan", "0")
        serials = _serials(result)
        assert "SN-PIX-006" not in serials

    async def test_storage_numeric_filter(self, devices: tuple[DeviceService, dict[str, Device]], search: SearchFn) -> None:
        svc, _ = devices
        result = await search(svc, "available_storage", "greaterThan", "200")
        assert _names(result) == ["Galaxy S24", "MacBook Pro"]
