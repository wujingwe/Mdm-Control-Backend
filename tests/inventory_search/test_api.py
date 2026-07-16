class TestInventorySearchAPI:
    BASE = "/api/v1/inventory-search"

    async def test_crud_flow(self, client):
        create = await client.post(self.BASE, json={
            "name": "Search1",
            "description": "desc",
            "created_by": 1,
        })
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

    async def test_list(self, client):
        await client.post(self.BASE, json={"name": "S1", "created_by": 1})
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1
