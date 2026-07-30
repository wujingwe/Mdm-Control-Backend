from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.extension_attributes.schemas import ExtensionAttributeCreate
from app.domains.extension_attributes.repositories import ExtensionAttributeRepository
from app.domains.extension_attributes.enums import ExtensionDataType, ExtensionInputType


class TestExtensionAttributesAPI:
    BASE = "/api/v1/extension-attributes"

    async def test_crud_flow(self, client: AsyncClient, db_session: AsyncSession) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Asset Tag",
                "dataType": "string",
                "inputType": "Text field",
            },
        )
        assert create.status_code == 201, create.json()
        aid = create.json()["id"]
        assert create.json()["name"] == "Asset Tag"

        get = await client.get(f"{self.BASE}/{aid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Asset Tag"

        update = await client.put(f"{self.BASE}/{aid}", json={"name": "Asset Tag Renamed"})
        assert update.status_code == 200
        assert update.json()["name"] == "Asset Tag Renamed"

        delete = await client.delete(f"{self.BASE}/{aid}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{aid}")
        assert get2.status_code == 404

    async def test_get_not_found(self, client: AsyncClient) -> None:
        resp = await client.get(f"{self.BASE}/999")
        assert resp.status_code == 404

    async def test_update_not_found(self, client: AsyncClient) -> None:
        resp = await client.put(f"{self.BASE}/999", json={"name": "Nope"})
        assert resp.status_code == 404

    async def test_delete_not_found(self, client: AsyncClient) -> None:
        resp = await client.delete(f"{self.BASE}/999")
        assert resp.status_code == 404

    async def test_list(self, client: AsyncClient, db_session: AsyncSession) -> None:
        repo = ExtensionAttributeRepository(db_session)
        for i in range(3):
            await repo.create(
                ExtensionAttributeCreate(
                    name=f"attr_{i}",
                    data_type=ExtensionDataType.STRING,
                    input_type=ExtensionInputType.TEXT_FIELD,
                ),
                created_by=1,
            )
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] == 3
