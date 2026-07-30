from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.models import Device
from app.domains.inventory_search.schemas import InventorySearchCreate
from app.domains.inventory_search.repositories import InventorySearchRepository


class TestInventorySearchAPI:
    BASE = "/api/v1/inventory-search"

    async def _seed_device(self, db_session: AsyncSession, name: str, serial: str, os_ver: str = "15.0") -> Device:
        d = Device(name=name, serial_number=serial, os_version=os_ver, connection_status="Connected", status="Enrolled")
        db_session.add(d)
        await db_session.commit()
        await db_session.refresh(d)
        return d

    async def test_crud_flow(self, client: AsyncClient, db_session: AsyncSession) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "My Search",
                "criteria": [{"field": "name", "operator": "is", "type": "string", "value": "test"}],
                "sortField": "name",
                "sortDirection": "asc",
            },
        )
        assert create.status_code == 201, create.json()
        sid = create.json()["id"]

        get = await client.get(f"{self.BASE}/{sid}")
        assert get.status_code == 200
        assert get.json()["name"] == "My Search"

        update = await client.put(f"{self.BASE}/{sid}", json={"name": "Renamed"})
        assert update.status_code == 200
        assert update.json()["name"] == "Renamed"

        delete = await client.delete(f"{self.BASE}/{sid}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{sid}")
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
        repo = InventorySearchRepository(db_session)
        for i in range(3):
            await repo.create(
                InventorySearchCreate(
                    name=f"s{i}",
                    criteria=[{"field": "name", "operator": "is", "type": "string", "value": "test"}],
                    sort_field="name",
                    sort_direction="asc",
                ),
                created_by=1,
            )
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] == 3

    async def test_execute(self, client: AsyncClient, db_session: AsyncSession) -> None:
        await self._seed_device(db_session, "A", "SN-A")
        await self._seed_device(db_session, "B", "SN-B")
        resp = await client.post(
            f"{self.BASE}/execute",
            json={
                "criteria": [{"field": "name", "operator": "is", "type": "string", "value": "A"}],
                "sortField": "name",
                "sortDirection": "asc",
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
