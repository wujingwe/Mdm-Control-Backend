import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.devices.models import Device


def _device_names(devices: list[dict]) -> list[str]:
    return sorted((d["name"] for d in devices), key=str.casefold)


def _device_serials(devices: list[dict]) -> list[str]:
    return sorted(d["serial_number"] for d in devices)


class TestInventorySearchAPI:
    BASE = "/api/v1/inventory-search"

    async def test_crud_flow(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Search1",
                "description": "desc",
                "created_by": 1,
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                    },
                ],
            },
        )
        assert create.status_code == 201
        sid = create.json()["id"]
        assert create.json()["name"] == "Search1"

        get = await client.get(f"{self.BASE}/{sid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Search1"

        update = await client.put(f"{self.BASE}/{sid}", json={"name": "Search2"})
        assert update.status_code == 200
        assert update.json()["name"] == "Search2"

        delete = await client.delete(f"{self.BASE}/{sid}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{sid}")
        assert get2.status_code == 404

    async def test_list(self, client: AsyncClient) -> None:
        await client.post(
            self.BASE,
            json={
                "name": "S1",
                "created_by": 1,
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                    }
                ],
            },
        )
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1

    async def test_create_with_criteria(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Online Android",
                "created_by": 1,
                "criteria": [
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Online",
                    },
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                    },
                ],
            },
        )
        assert create.status_code == 201
        criteria = create.json()["criteria"]
        assert len(criteria) == 2
        assert criteria[0]["field"] == "connection_status"
        assert criteria[1]["field"] == "os_version"

    async def test_get_returns_criteria(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Low Battery",
                "created_by": 1,
                "criteria": [
                    {
                        "field": "battery_status",
                        "operator": "lessThan",
                        "type": "number",
                        "value": "20",
                    },
                ],
            },
        )
        sid = create.json()["id"]
        get = await client.get(f"{self.BASE}/{sid}")
        assert get.status_code == 200
        criteria = get.json()["criteria"]
        assert len(criteria) == 1
        assert criteria[0]["field"] == "battery_status"

    async def test_update_criteria(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Test Search",
                "created_by": 1,
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                    },
                ],
            },
        )
        sid = create.json()["id"]
        update = await client.put(
            f"{self.BASE}/{sid}",
            json={
                "criteria": [
                    {
                        "field": "battery_status",
                        "operator": "lessThan",
                        "type": "number",
                        "value": "15",
                    },
                ],
            },
        )
        assert update.status_code == 200
        criteria = update.json()["criteria"]
        assert len(criteria) == 1
        assert criteria[0]["field"] == "battery_status"

    async def test_update_empty_criteria_rejected(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Test Search",
                "created_by": 1,
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                    },
                ],
            },
        )
        sid = create.json()["id"]
        update = await client.put(
            f"{self.BASE}/{sid}",
            json={"criteria": []},
        )
        assert update.status_code == 422

    async def test_create_with_invalid_criteria_type(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Bad Search",
                "created_by": 1,
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "invalid",
                        "value": "test",
                    },
                ],
            },
        )
        assert create.status_code == 422

    async def test_create_with_criteria_parentheses(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Complex Search",
                "created_by": 1,
                "criteria": [
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Online",
                        "left_parentheses": True,
                    },
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                        "right_parentheses": True,
                    },
                ],
            },
        )
        assert create.status_code == 201
        criteria = create.json()["criteria"]
        assert criteria[0]["left_parentheses"] is True
        assert criteria[1]["right_parentheses"] is True


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
                connection_status="Online",
                status="Enrolled",
                battery_status=95,
                total_storage=1000,
                available_storage=500,
            ),
            Device(
                name="MacBook Air",
                serial_number="SN-MBA-002",
                os_version="macOS 14.5",
                connection_status="Online",
                status="Enrolled",
                battery_status=30,
                total_storage=512,
                available_storage=200,
            ),
            Device(
                name="iPhone 15",
                serial_number="SN-IP15-003",
                os_version="iOS 18.1",
                connection_status="Offline",
                status="Enrolled",
                battery_status=10,
                total_storage=256,
                available_storage=100,
            ),
            Device(
                name="iPhone SE",
                serial_number="SN-IPSE-004",
                os_version="iOS 17.4",
                connection_status="Online",
                status="Pending",
                battery_status=80,
                total_storage=128,
                available_storage=64,
            ),
            Device(
                name="Galaxy S24",
                serial_number="SN-GS24-005",
                os_version="Android 14",
                connection_status="Offline",
                status="Unknown",
                battery_status=50,
                total_storage=256,
                available_storage=256,
            ),
            Device(
                name="Pixel 8",
                serial_number="SN-PIX-006",
                os_version="Android 15",
                connection_status="Online",
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
                        "value": "Online",
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "value": "Online",
                        "and_or": "AND",
                    },
                    {
                        "field": "status",
                        "operator": "is",
                        "type": "string",
                        "value": "Enrolled",
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "AND",
                    },
                    {
                        "field": "status",
                        "operator": "is",
                        "type": "string",
                        "value": "Enrolled",
                        "and_or": "AND",
                    },
                    {
                        "field": "battery_status",
                        "operator": "greaterThan",
                        "type": "number",
                        "value": "5",
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "OR",
                    },
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 15",
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "OR",
                    },
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "iPhone",
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "AND",
                        "left_parentheses": True,
                    },
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Online",
                        "and_or": "OR",
                        "right_parentheses": True,
                    },
                    {
                        "field": "os_version",
                        "operator": "like",
                        "type": "string",
                        "value": "iOS",
                        "and_or": "AND",
                        "left_parentheses": True,
                    },
                    {
                        "field": "status",
                        "operator": "is",
                        "type": "string",
                        "value": "Enrolled",
                        "and_or": "AND",
                        "right_parentheses": True,
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "OR",
                        "left_parentheses": True,
                    },
                    {
                        "field": "name",
                        "operator": "like",
                        "type": "string",
                        "value": "Pixel",
                        "and_or": "AND",
                        "right_parentheses": True,
                    },
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Online",
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "OR",
                        "left_parentheses": True,
                        "right_parentheses": True,
                    },
                    {
                        "field": "os_version",
                        "operator": "like",
                        "type": "string",
                        "value": "iOS",
                        "and_or": "OR",
                        "left_parentheses": True,
                        "right_parentheses": True,
                    },
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                        "and_or": "AND",
                        "left_parentheses": True,
                        "right_parentheses": True,
                    },
                ],
            },
        )
        assert resp.status_code == 200
        names = _device_names(resp.json())
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
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        device = body[0]
        assert device["name"] == "iPhone 15"
        assert device["serial_number"] == "SN-IP15-003"
        assert device["os_version"] == "iOS 18.1"
        assert device["connection_status"] == "Offline"
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
                        "and_or": "AND",
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
                        "and_or": "AND",
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
                        "and_or": "AND",
                    },
                ],
            },
        )
        assert resp.status_code == 422
