from httpx import AsyncClient


class TestProfilesAPI:
    BASE = "/api/v1/profiles"

    async def test_crud_flow(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Profile1",
                "description": "desc",
            },
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        assert create.json()["name"] == "Profile1"

        get = await client.get(f"{self.BASE}/{pid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Profile1"

        update = await client.put(f"{self.BASE}/{pid}", json={"name": "Profile2"})
        assert update.status_code == 200
        assert update.json()["name"] == "Profile2"

        delete = await client.delete(f"{self.BASE}/{pid}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{pid}")
        assert get2.status_code == 404

    async def test_list(self, client: AsyncClient) -> None:
        await client.post(self.BASE, json={"name": "P1"})
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1

    async def test_set_scope(self, client: AsyncClient) -> None:
        create = await client.post(self.BASE, json={"name": "P"})
        pid = create.json()["id"]
        resp = await client.put(
            f"{self.BASE}/{pid}/scope",
            json={
                "targets": [{"scope_type": "ALL_DEVICES"}],
                "exclusions": [],
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["targets"]) == 1

    async def test_get_scope(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "P2",
                "scope": {
                    "targets": [{"scope_type": "SMART_GROUP", "target_id": 1}],
                    "exclusions": [],
                },
            },
        )
        pid = create.json()["id"]
        resp = await client.get(f"{self.BASE}/{pid}/scope")
        assert resp.status_code == 200
        assert len(resp.json()["targets"]) == 1

    async def test_get_assignments_empty(self, client: AsyncClient) -> None:
        create = await client.post(self.BASE, json={"name": "P"})
        pid = create.json()["id"]
        resp = await client.get(f"{self.BASE}/{pid}/assignments")
        assert resp.status_code == 200
        assert resp.json() == []
