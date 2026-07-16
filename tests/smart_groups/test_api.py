class TestSmartGroupsAPI:
    BASE = "/api/v1/smart-groups"

    async def test_crud_flow(self, client):
        create = await client.post(self.BASE, json={
            "name": "Smart Group A",
            "description": "desc",
        })
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
        assert delete.status_code == 200

        get2 = await client.get(f"{self.BASE}/{gid}")
        assert get2.status_code == 404

    async def test_list(self, client):
        await client.post(self.BASE, json={"name": "SG1"})
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1
        assert all(g["name"] is not None for g in data["items"])

    async def test_update_empty_body(self, client):
        create = await client.post(self.BASE, json={"name": "G"})
        gid = create.json()["id"]
        resp = await client.put(f"{self.BASE}/{gid}", json={})
        assert resp.status_code == 200
