from httpx import AsyncClient


class TestSmartGroupsAPI:
    BASE = "/api/v1/smart-groups"

    async def test_crud_flow(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Smart Group A",
                "description": "desc",
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
        gid = create.json()["id"]
        assert create.json()["name"] == "Smart Group A"

        get = await client.get(f"{self.BASE}/{gid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Smart Group A"

        update = await client.put(f"{self.BASE}/{gid}", json={"name": "Smart Group B"})
        assert update.status_code == 200
        assert update.json()["name"] == "Smart Group B"

        delete = await client.delete(f"{self.BASE}/{gid}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{gid}")
        assert get2.status_code == 404

    async def test_list(self, client: AsyncClient) -> None:
        await client.post(
            self.BASE,
            json={
                "name": "SG1",
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
        assert all(g["name"] is not None for g in data["items"])

    async def test_update_empty_body(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "G",
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
        gid = create.json()["id"]
        resp = await client.put(f"{self.BASE}/{gid}", json={})
        assert resp.status_code == 200

    async def test_create_with_criteria(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Android Group",
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
        criteria = create.json()["criteria"]
        assert len(criteria) == 1
        assert criteria[0]["field"] == "os_version"
        assert criteria[0]["operator"] == "is"
        assert criteria[0]["type"] == "string"
        assert criteria[0]["value"] == "Android 14"

    async def test_create_with_multiple_criteria(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Complex Group",
                "criteria": [
                    {
                        "field": "os_version",
                        "operator": "is",
                        "type": "string",
                        "value": "Android 14",
                    },
                    {
                        "field": "battery_status",
                        "operator": "lessThan",
                        "type": "number",
                        "value": "20",
                        "leftParentheses": True,
                    },
                    {
                        "field": "connection_status",
                        "operator": "is",
                        "type": "string",
                        "value": "Connected",
                        "rightParentheses": True,
                    },
                ],
            },
        )
        assert create.status_code == 201
        criteria = create.json()["criteria"]
        assert len(criteria) == 3
        assert criteria[0]["field"] == "os_version"
        assert criteria[1]["leftParentheses"] is True
        assert criteria[2]["rightParentheses"] is True

    async def test_get_returns_criteria(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Test Group",
                "criteria": [
                    {
                        "field": "compliance",
                        "operator": "is",
                        "type": "string",
                        "value": "Non-compliant",
                    },
                ],
            },
        )
        gid = create.json()["id"]
        get = await client.get(f"{self.BASE}/{gid}")
        assert get.status_code == 200
        criteria = get.json()["criteria"]
        assert len(criteria) == 1
        assert criteria[0]["field"] == "compliance"

    async def test_update_criteria(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Test Group",
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
        gid = create.json()["id"]
        update = await client.put(
            f"{self.BASE}/{gid}",
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

    async def test_update_empty_criteria_accepted(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Test Group",
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
        gid = create.json()["id"]
        update = await client.put(
            f"{self.BASE}/{gid}",
            json={"criteria": []},
        )
        assert update.status_code == 200

    async def test_create_without_criteria_rejected(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={"name": "No Criteria Group"},
        )
        assert create.status_code == 422

    async def test_create_with_empty_criteria_rejected(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={"name": "Empty Criteria Group", "criteria": []},
        )
        assert create.status_code == 422

    async def test_create_with_invalid_criteria_type(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Bad Group",
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

    async def test_create_with_missing_criteria_field(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Bad Group",
                "criteria": [
                    {
                        "operator": "is",
                        "type": "string",
                        "value": "test",
                    },
                ],
            },
        )
        assert create.status_code == 422
