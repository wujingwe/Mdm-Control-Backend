from httpx import AsyncClient


class TestExtensionAttributesAPI:
    BASE = "/api/v1/extension-attributes"

    async def test_crud_flow(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Ext1",
                "dataType": "string",
                "inputType": "Text field",
            },
        )
        assert create.status_code == 201
        eid = create.json()["id"]
        assert create.json()["name"] == "Ext1"

        get = await client.get(f"{self.BASE}/{eid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Ext1"

        update = await client.put(f"{self.BASE}/{eid}", json={"name": "Ext2"})
        assert update.status_code == 200
        assert update.json()["name"] == "Ext2"

        delete = await client.delete(f"{self.BASE}/{eid}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{eid}")
        assert get2.status_code == 404

    async def test_list(self, client: AsyncClient) -> None:
        await client.post(
            self.BASE,
            json={
                "name": "Ext1",
                "dataType": "string",
                "inputType": "Text field",
            },
        )
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1
