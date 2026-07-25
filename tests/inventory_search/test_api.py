import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.criteria import Criteria
from app.common.enums import CriteriaType
from app.devices.models import Device
from app.inventory_search.models import InventorySearch


async def _seed_search(db: AsyncSession, **kwargs) -> InventorySearch:
    defaults = dict(
        name="Default Search",
        criteria=[
            Criteria(
                field="os_version",
                operator="is",
                type=CriteriaType.STRING,
                value="Android 14",
            )
        ],
        created_by=1,
    )
    defaults.update(kwargs)
    if (
        isinstance(defaults["criteria"], list)
        and defaults["criteria"]
        and hasattr(defaults["criteria"][0], "model_dump")
    ):
        defaults["criteria"] = [c.model_dump() for c in defaults["criteria"]]
    item = InventorySearch(**defaults)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


class TestInventorySearchAPI:
    BASE = "/api/v1/inventory-search"

    async def test_crud_flow(self, client: AsyncClient, db_session: AsyncSession) -> None:
        search = await _seed_search(db_session, name="Search1")

        get = await client.get(f"{self.BASE}/{search.id}")
        assert get.status_code == 200
        assert get.json()["name"] == "Search1"

        update = await client.put(f"{self.BASE}/{search.id}", json={"name": "Search2"})
        assert update.status_code == 200
        assert update.json()["name"] == "Search2"

        delete = await client.delete(f"{self.BASE}/{search.id}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{search.id}")
        assert get2.status_code == 404

    async def test_list(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await _seed_search(db_session, name="S1")

        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1

    async def test_get_returns_criteria(self, client: AsyncClient, db_session: AsyncSession) -> None:
        criteria = [
            Criteria(
                field="battery_status",
                operator="lessThan",
                type=CriteriaType.NUMBER,
                value="20",
            ),
        ]
        search = await _seed_search(db_session, name="Low Battery", criteria=criteria)

        get = await client.get(f"{self.BASE}/{search.id}")
        assert get.status_code == 200
        resp_criteria = get.json()["criteria"]
        assert len(resp_criteria) == 1
        assert resp_criteria[0]["field"] == "battery_status"

    async def test_update_criteria(self, client: AsyncClient, db_session: AsyncSession) -> None:
        search = await _seed_search(db_session, name="Test Search")

        new_criteria = [
            {
                "field": "battery_status",
                "operator": "lessThan",
                "type": "number",
                "value": "15",
            },
        ]
        update = await client.put(
            f"{self.BASE}/{search.id}",
            json={"criteria": new_criteria},
        )
        assert update.status_code == 200
        criteria = update.json()["criteria"]
        assert len(criteria) == 1
        assert criteria[0]["field"] == "battery_status"

    async def test_update_empty_criteria_rejected(self, client: AsyncClient, db_session: AsyncSession) -> None:
        search = await _seed_search(db_session, name="Test Search")

        update = await client.put(
            f"{self.BASE}/{search.id}",
            json={"criteria": []},
        )
        assert update.status_code == 422

    async def test_get_not_found(self, client: AsyncClient) -> None:
        resp = await client.get(f"{self.BASE}/9999")
        assert resp.status_code == 404

    async def test_delete_nonexistent_returns_204(self, client: AsyncClient) -> None:
        resp = await client.delete(f"{self.BASE}/9999")
        assert resp.status_code == 204

    async def test_list_returns_response_shape(self, client: AsyncClient, db_session: AsyncSession) -> None:
        criteria = [
            Criteria(
                field="os_version",
                operator="is",
                type=CriteriaType.STRING,
                value="Android 14",
            ),
        ]
        await _seed_search(db_session, name="SearchA", criteria=criteria)
        await _seed_search(db_session, name="SearchB", criteria=criteria)

        resp = await client.get(self.BASE)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2
        assert all("name" in item for item in data["items"])

    async def test_get_returns_all_fields(self, client: AsyncClient, db_session: AsyncSession) -> None:
        criteria = [
            Criteria(
                field="connection_status",
                operator="is",
                type=CriteriaType.STRING,
                value="Connected",
            ),
            Criteria(
                field="os_version",
                operator="is",
                type=CriteriaType.STRING,
                value="Android 14",
            ),
        ]
        search = await _seed_search(db_session, name="Online Android", criteria=criteria)

        get = await client.get(f"{self.BASE}/{search.id}")
        assert get.status_code == 200
        body = get.json()
        assert body["name"] == "Online Android"
        assert body["createdBy"] == 1
        assert len(body["criteria"]) == 2
        assert body["criteria"][0]["field"] == "connection_status"
        assert body["criteria"][1]["field"] == "os_version"


EXECUTE = "/api/v1/inventory-search/execute"


class TestExecuteSearch:
    """Tests for POST /inventory-search/execute."""

    @pytest.fixture(autouse=True)
    async def seed_devices(self, db_session: AsyncSession) -> None:
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
                connection_status="Connected",
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

    # ── single criterion ──────────────────────────────────────────────

    async def test_is_operator(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Connected",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["iPhone SE", "MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_is_not_operator(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "status",
                        "operator": "isNot",
                        "type": "string",
                        "value": "Enrolled",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["Galaxy S24", "iPhone SE"]

    async def test_like_operator(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "Mac",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["MacBook Air", "MacBook Pro"]

    async def test_greater_than_operator(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "battery_status",
                        "operator": "greaterThan",
                        "type": "number",
                        "value": "80",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["MacBook Pro"]

    async def test_less_than_operator(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "battery_status",
                        "operator": "lessThan",
                        "type": "number",
                        "value": "30",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["iPhone 15"]

    async def test_regex_operator(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "matchesRegex",
                        "type": "string",
                        "value": "^macOS",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["MacBook Air", "MacBook Pro"]

    # ── multiple criteria (AND) ───────────────────────────────────────

    async def test_two_criteria_and(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Connected",
                        "andOr": "AND",
                    },
                    {
                        "field": "status",
                        "operator": "is",
                        "type": "string",
                        "value": "Enrolled",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_three_criteria_and(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "like",
                        "type": "string",
                        "value": "iOS",
                        "andOr": "AND",
                    },
                    {
                        "field": "status",
                        "operator": "is",
                        "type": "string",
                        "value": "Enrolled",
                        "andOr": "AND",
                    },
                    {
                        "field": "battery_status",
                        "operator": "greaterThan",
                        "type": "number",
                        "value": "5",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["iPhone 15"]

    # ── multiple criteria (OR) ────────────────────────────────────────

    async def test_two_criteria_or(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "macOS 15.0",
                        "andOr": "OR",
                    },
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 15",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["MacBook Pro", "Pixel 8"]

    async def test_or_like_name(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "Mac",
                        "andOr": "OR",
                    },
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "iPhone",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["iPhone 15", "iPhone SE", "MacBook Air", "MacBook Pro"]

    # ── parentheses grouping ──────────────────────────────────────────

    async def test_and_group_or_and_group(self, client: AsyncClient) -> None:
        """(name LIKE 'Mac' AND connection_status IS 'Online')
        OR (os_version LIKE 'iOS' AND status IS 'Enrolled')"""
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "Mac",
                        "andOr": "AND",
                        "leftParentheses": True,
                    },
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Connected",
                        "andOr": "OR",
                        "rightParentheses": True,
                    },
                    {
                        "field": "os_version",
                        "operator": "like",
                        "type": "string",
                        "value": "iOS",
                        "andOr": "AND",
                        "leftParentheses": True,
                    },
                    {
                        "field": "status",
                        "operator": "is",
                        "type": "string",
                        "value": "Enrolled",
                        "andOr": "AND",
                        "rightParentheses": True,
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["iPhone 15", "MacBook Air", "MacBook Pro"]

    async def test_or_group_and(self, client: AsyncClient) -> None:
        """(name LIKE 'Mac' OR name LIKE 'Pixel')
        AND connection_status IS 'Online'"""
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "Mac",
                        "andOr": "OR",
                        "leftParentheses": True,
                    },
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "Pixel",
                        "andOr": "AND",
                        "rightParentheses": True,
                    },
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Connected",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == ["MacBook Air", "MacBook Pro", "Pixel 8"]

    async def test_three_parenthesized_groups(self, client: AsyncClient) -> None:
        """(name LIKE 'Mac') OR (os_version LIKE 'iOS')
        OR (os_version IS 'Android 14')"""
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "Mac",
                        "andOr": "OR",
                        "leftParentheses": True,
                        "rightParentheses": True,
                    },
                    {
                        "field": "os_version",
                        "operator": "like",
                        "type": "string",
                        "value": "iOS",
                        "andOr": "OR",
                        "leftParentheses": True,
                        "rightParentheses": True,
                    },
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                        "andOr": "AND",
                        "leftParentheses": True,
                        "rightParentheses": True,
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = sorted((d["name"] for d in resp.json()), key=str.casefold)
        assert names == [
            "Galaxy S24",
            "iPhone 15",
            "iPhone SE",
            "MacBook Air",
            "MacBook Pro",
        ]

    # ── response shape ────────────────────────────────────────────────

    async def test_response_contains_device_fields(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "name",
                        "operator": "is",
                        "type": "string",
                        "value": "iPhone 15",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        device = body[0]
        assert device["name"] == "iPhone 15"
        assert device["serialNumber"] == "SN-IP15-003"
        assert device["osVersion"] == "iOS 18.1"
        assert device["connectionStatus"] == "Disconnected"
        assert device["status"] == "Enrolled"

    async def test_empty_result(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "name",
                        "operator": "is",
                        "type": "string",
                        "value": "NonExistent Device",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_no_match_returns_all(self, client: AsyncClient) -> None:
        """Unknown field is skipped → returns all 6 devices."""
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "nonexistent_field",
                        "operator": "is",
                        "type": "string",
                        "value": "anything",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 6

    # ── validation ────────────────────────────────────────────────────

    async def test_empty_criteria_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(EXECUTE, json={"criteria": []})
        assert resp.status_code == 422

    async def test_missing_criteria_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(EXECUTE, json={})
        assert resp.status_code == 422

    async def test_invalid_type_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(
            EXECUTE,
            json={
                "criteria": [
                    {
                        "field": "name",
                        "operator": "is",
                        "type": "INVALID",
                        "value": "test",
                        "andOr": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 422
