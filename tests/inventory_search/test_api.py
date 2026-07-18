from httpx import AsyncClient
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
                    {"field": "os_version", "operator": "is", "type": "string", "value": "Android 14"},
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
        assert delete.status_code == 200

        get2 = await client.get(f"{self.BASE}/{sid}")
        assert get2.status_code == 404

    async def test_list(self, client: AsyncClient) -> None:
        await client.post(
            self.BASE,
            json={
                "name": "S1",
                "created_by": 1,
                "criteria": [{"field": "os_version", "operator": "is", "type": "string", "value": "Android 14"}],
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
