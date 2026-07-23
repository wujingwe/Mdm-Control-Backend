import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ConnectionStatus
from app.criteria.schemas import Criteria
from app.devices.models import Device
from app.inventory_search.repositories import InventorySearchRepository
from app.inventory_search.schemas import InventorySearchExecuteRequest
from app.inventory_search.services import InventorySearchService


@pytest.fixture
async def devices(
    db_session: AsyncSession,
) -> tuple[InventorySearchService, dict[str, Device]]:
    """Create 6 devices with diverse attributes for filtering tests."""
    devs = [
        Device(
            name="MacBook Pro",
            serial_number="SN-MBP-001",
            os_version="macOS 15.0",
            connection_status="Connected",
            status="Enrolled",
            battery_status=95,
            total_storage=1000,
            available_storage=500,
        ),
        Device(
            name="MacBook Air",
            serial_number="SN-MBA-002",
            os_version="macOS 14.5",
            connection_status="Connected",
            status="Enrolled",
            battery_status=30,
            total_storage=512,
            available_storage=200,
        ),
        Device(
            name="iPhone 15",
            serial_number="SN-IP15-003",
            os_version="iOS 18.1",
            connection_status="Disconnected",
            status="Enrolled",
            battery_status=10,
            total_storage=256,
            available_storage=100,
        ),
        Device(
            name="iPhone SE",
            serial_number="SN-IPSE-004",
            os_version="iOS 17.4",
            connection_status=ConnectionStatus.CONNECTED,
            status="Pending",
            battery_status=80,
            total_storage=128,
            available_storage=64,
        ),
        Device(
            name="Galaxy S24",
            serial_number="SN-GS24-005",
            os_version="Android 14",
            connection_status="Disconnected",
            status="Unknown",
            battery_status=50,
            total_storage=256,
            available_storage=256,
        ),
        Device(
            name="Pixel 8",
            serial_number="SN-PIX-006",
            os_version="Android 15",
            connection_status="Connected",
            status="Enrolled",
            battery_status=None,
            total_storage=128,
            available_storage=None,
        ),
    ]
    db_session.add_all(devs)
    await db_session.commit()
    repo = InventorySearchRepository(db_session)
    return InventorySearchService(repo), {d.serial_number: d for d in devs}


async def _search(
    service: InventorySearchService,
    field: str,
    operator: str,
    value: str,
    and_or: str = "AND",
) -> list[Device]:
    return await service.execute_search(
        InventorySearchExecuteRequest(
            criteria=[
                Criteria(
                    field=field,
                    operator=operator,
                    type="string",
                    value=value,
                    and_or=and_or,
                )
            ],
        )
    )


def _names(result: list[Device]) -> list[str]:
    """Extract names from search result, sorted case-insensitively."""
    return sorted((d.name for d in result), key=str.casefold)


def _serials(result: list[Device]) -> list[str]:
    """Extract serial_numbers from search result."""
    return sorted(d.serial_number for d in result)


class TestSearchIsOperator:
    async def test_is_online(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "connection_status", "is", "Connected")
        assert _names(result) == ["iPhone SE", "MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_is_offline(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "connection_status", "is", "Disconnected")
        assert _names(result) == ["Galaxy S24", "iPhone 15"]

    async def test_is_enrolled(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "status", "is", "Enrolled")
        assert _names(result) == ["iPhone 15", "MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_is_exact_name(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "name", "is", "iPhone 15")
        assert len(result) == 1
        assert result[0].name == "iPhone 15"


class TestSearchIsNotOperator:
    async def test_is_not_offline(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "connection_status", "isNot", "Disconnected")
        assert _names(result) == ["iPhone SE", "MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_is_not_enrolled(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "status", "isNot", "Enrolled")
        assert _names(result) == ["Galaxy S24", "iPhone SE"]


class TestSearchLikeOperator:
    async def test_like_mac(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "name", "like", "Mac")
        assert _names(result) == ["MacBook Air", "MacBook Pro"]

    async def test_like_iphone(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "name", "like", "iPhone")
        assert _names(result) == ["iPhone 15", "iPhone SE"]

    async def test_like_os_version_android(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "os_version", "like", "Android")
        assert _names(result) == ["Galaxy S24", "Pixel 8"]


class TestSearchNotLikeOperator:
    async def test_not_like_mac(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "name", "notLike", "Mac")
        assert _names(result) == ["Galaxy S24", "iPhone 15", "iPhone SE", "Pixel 8"]

    async def test_not_like_ios(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "os_version", "notLike", "iOS")
        assert _names(result) == ["Galaxy S24", "MacBook Air", "MacBook Pro", "Pixel 8"]


class TestSearchGreaterThanOperator:
    async def test_greater_than_80_battery(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "greaterThan", "80")
        assert _names(result) == ["MacBook Pro"]

    async def test_greater_than_50_battery(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "greaterThan", "50")
        assert _names(result) == ["iPhone SE", "MacBook Pro"]

    async def test_greater_than_excludes_none(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "greaterThan", "0")
        assert _names(result) == [
            "Galaxy S24",
            "iPhone 15",
            "iPhone SE",
            "MacBook Air",
            "MacBook Pro",
        ]


class TestSearchLessThanOperator:
    async def test_less_than_30_battery(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "lessThan", "30")
        assert _names(result) == ["iPhone 15"]

    async def test_less_than_50_battery(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "lessThan", "50")
        assert _names(result) == ["iPhone 15", "MacBook Air"]


class TestSearchGreaterThanOrEqualOperator:
    async def test_gte_80(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "greaterThanOrEqual", "80")
        assert _names(result) == ["iPhone SE", "MacBook Pro"]

    async def test_gte_50(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "greaterThanOrEqual", "50")
        assert _names(result) == ["Galaxy S24", "iPhone SE", "MacBook Pro"]


class TestSearchLessThanOrEqualOperator:
    async def test_lte_30(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "lessThanOrEqual", "30")
        assert _names(result) == ["iPhone 15", "MacBook Air"]

    async def test_lte_50(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "lessThanOrEqual", "50")
        assert _names(result) == ["Galaxy S24", "iPhone 15", "MacBook Air"]


class TestSearchRegexOperator:
    async def test_matches_regex(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "os_version", "matchesRegex", "^macOS")
        assert _names(result) == ["MacBook Air", "MacBook Pro"]

    async def test_does_not_match_regex(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "os_version", "doesNotMatchRegex", "^macOS")
        assert _names(result) == ["Galaxy S24", "iPhone 15", "iPhone SE", "Pixel 8"]

    async def test_regex_partial_match(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "name", "matchesRegex", "^.*\\s(Pro|Air)$")
        assert _names(result) == ["MacBook Air", "MacBook Pro"]


class TestSearchConjunctions:
    async def test_and_online_enrolled(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="connection_status",
                        operator="is",
                        type="string",
                        value="Connected",
                        and_or="AND",
                    ),
                    Criteria(
                        field="status",
                        operator="is",
                        type="string",
                        value="Enrolled",
                        and_or="AND",
                    ),
                ],
            )
        )
        assert _names(result) == ["MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_or_online_or_enrolled(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="name",
                        operator="like",
                        type="string",
                        value="Mac",
                        and_or="OR",
                    ),
                    Criteria(
                        field="name",
                        operator="like",
                        type="string",
                        value="iPhone",
                        and_or="AND",
                    ),
                ],
            )
        )
        assert _names(result) == [
            "iPhone 15",
            "iPhone SE",
            "MacBook Air",
            "MacBook Pro",
        ]

    async def test_and_no_match(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "connection_status", "is", "Connected")
        online = _names(result)
        result2 = await _search(svc, "status", "is", "Needs attention")
        needs_attention = _names(result2)
        assert len(set(online) & set(needs_attention)) == 0


class TestSearchMultiCriteria:
    async def test_three_criteria_and(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="os_version",
                        operator="like",
                        type="string",
                        value="iOS",
                        and_or="AND",
                    ),
                    Criteria(
                        field="status",
                        operator="is",
                        type="string",
                        value="Enrolled",
                        and_or="AND",
                    ),
                    Criteria(
                        field="battery_status",
                        operator="greaterThan",
                        type="number",
                        value="5",
                        and_or="AND",
                    ),
                ],
            )
        )
        assert _names(result) == ["iPhone 15"]

    async def test_two_criteria_or(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="os_version",
                        operator="is",
                        type="string",
                        value="macOS 15.0",
                        and_or="OR",
                    ),
                    Criteria(
                        field="os_version",
                        operator="is",
                        type="string",
                        value="Android 15",
                        and_or="AND",
                    ),
                ],
            )
        )
        assert _names(result) == ["MacBook Pro", "Pixel 8"]

    async def test_criteria_across_different_fields(
        self, devices: tuple[InventorySearchService, dict[str, Device]]
    ) -> None:
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="connection_status",
                        operator="is",
                        type="string",
                        value="Connected",
                        and_or="AND",
                    ),
                    Criteria(
                        field="status",
                        operator="isNot",
                        type="string",
                        value="Pending",
                        and_or="AND",
                    ),
                    Criteria(
                        field="name",
                        operator="notLike",
                        type="string",
                        value="Pixel",
                        and_or="AND",
                    ),
                ],
            )
        )
        assert _names(result) == ["MacBook Air", "MacBook Pro"]


class TestSearchParentheses:
    """Tests for parentheses grouping with mixed AND/OR conjunctions."""

    async def test_and_group_or_and_group(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        """(name LIKE 'Mac' AND connection_status IS 'Online') OR (os_version LIKE 'iOS' AND status IS 'Enrolled')"""
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="name",
                        operator="like",
                        type="string",
                        value="Mac",
                        and_or="AND",
                        left_parentheses=True,
                    ),
                    Criteria(
                        field="connection_status",
                        operator="is",
                        type="string",
                        value="Connected",
                        and_or="OR",
                        right_parentheses=True,
                    ),
                    Criteria(
                        field="os_version",
                        operator="like",
                        type="string",
                        value="iOS",
                        and_or="AND",
                        left_parentheses=True,
                    ),
                    Criteria(
                        field="status",
                        operator="is",
                        type="string",
                        value="Enrolled",
                        and_or="AND",
                        right_parentheses=True,
                    ),
                ],
            )
        )
        # (Mac AND Online) = MacBook Pro, MacBook Air
        # (iOS AND Enrolled) = iPhone 15
        assert _names(result) == ["iPhone 15", "MacBook Air", "MacBook Pro"]

    async def test_or_group_and_group(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        """(name LIKE 'Mac' OR name LIKE 'iPhone') AND connection_status IS 'Online'"""
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="name",
                        operator="like",
                        type="string",
                        value="Mac",
                        and_or="OR",
                        left_parentheses=True,
                    ),
                    Criteria(
                        field="name",
                        operator="like",
                        type="string",
                        value="iPhone",
                        and_or="AND",
                        right_parentheses=True,
                    ),
                    Criteria(
                        field="connection_status",
                        operator="is",
                        type="string",
                        value="Connected",
                        and_or="AND",
                    ),
                ],
            )
        )
        # (Mac OR iPhone) = MacBook Pro, MacBook Air, iPhone 15, iPhone SE
        # AND Online = MacBook Pro, MacBook Air, iPhone SE
        assert _names(result) == ["iPhone SE", "MacBook Air", "MacBook Pro"]

    async def test_single_parenthesized_group(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        """(name LIKE 'Mac' AND status IS 'Enrolled')"""
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="name",
                        operator="like",
                        type="string",
                        value="Mac",
                        and_or="AND",
                        left_parentheses=True,
                    ),
                    Criteria(
                        field="status",
                        operator="is",
                        type="string",
                        value="Enrolled",
                        and_or="AND",
                        right_parentheses=True,
                    ),
                ],
            )
        )
        assert _names(result) == ["MacBook Air", "MacBook Pro"]

    async def test_no_parens_same_as_single_group(
        self, devices: tuple[InventorySearchService, dict[str, Device]]
    ) -> None:
        """Without parentheses, all criteria form one group (flat chain)."""
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="name",
                        operator="like",
                        type="string",
                        value="Mac",
                        and_or="AND",
                    ),
                    Criteria(
                        field="status",
                        operator="is",
                        type="string",
                        value="Enrolled",
                        and_or="AND",
                    ),
                ],
            )
        )
        assert _names(result) == ["MacBook Air", "MacBook Pro"]

    async def test_three_groups(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        """(name LIKE 'Mac') OR (os_version LIKE 'iOS') OR (os_version LIKE 'Android 14')"""
        svc, _ = devices
        result = await svc.execute_search(
            InventorySearchExecuteRequest(
                criteria=[
                    Criteria(
                        field="name",
                        operator="like",
                        type="string",
                        value="Mac",
                        and_or="OR",
                        left_parentheses=True,
                        right_parentheses=True,
                    ),
                    Criteria(
                        field="os_version",
                        operator="like",
                        type="string",
                        value="iOS",
                        and_or="OR",
                        left_parentheses=True,
                        right_parentheses=True,
                    ),
                    Criteria(
                        field="os_version",
                        operator="is",
                        type="string",
                        value="Android 14",
                        and_or="AND",
                        left_parentheses=True,
                        right_parentheses=True,
                    ),
                ],
            )
        )
        # Mac = MacBook Pro, MacBook Air
        # iOS = iPhone 15, iPhone SE
        # Android 14 = Galaxy S24
        assert _names(result) == [
            "Galaxy S24",
            "iPhone 15",
            "iPhone SE",
            "MacBook Air",
            "MacBook Pro",
        ]


class TestSearchEdgeCases:
    async def test_no_match_returns_empty(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "name", "is", "NonExistent Device")
        assert result == []

    async def test_unknown_field_returns_all(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "nonexistent_field", "is", "value")
        assert len(result) == 6

    async def test_battery_status_none_excluded_from_numeric(
        self, devices: tuple[InventorySearchService, dict[str, Device]]
    ) -> None:
        svc, _ = devices
        result = await _search(svc, "battery_status", "greaterThan", "0")
        serials = _serials(result)
        assert "SN-PIX-006" not in serials

    async def test_storage_numeric_filter(self, devices: tuple[InventorySearchService, dict[str, Device]]) -> None:
        svc, _ = devices
        result = await _search(svc, "available_storage", "greaterThan", "200")
        assert _names(result) == ["Galaxy S24", "MacBook Pro"]
