from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


class TestStaticGroupsAPI:
    BASE = "/api/v1/static-groups"

    async def test_crud_flow(self, client: AsyncClient, db_session: AsyncSession) -> None:
        from app.devices.models import Device

        dev1 = Device(
            name="D1",
            serial_number="SN001",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev2 = Device(
            name="D2",
            serial_number="SN002",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        dev3 = Device(
            name="D3",
            serial_number="SN003",
            os_version="14",
            connection_status="Connected",
            status="Enrolled",
        )
        db_session.add_all([dev1, dev2, dev3])
        await db_session.commit()

        create = await client.post(
            self.BASE,
            json={
                "name": "Static Group A",
                "description": "desc",
                "device_serial_numbers": ["SN001", "SN002"],
            },
        )
        assert create.status_code == 201
        gid = create.json()["id"]
        assert create.json()["name"] == "Static Group A"
        assert {d["serial_number"] for d in create.json()["devices"]} == {
            "SN001",
            "SN002",
        }

        get = await client.get(f"{self.BASE}/{gid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Static Group A"
        assert {d["serial_number"] for d in get.json()["devices"]} == {"SN001", "SN002"}

        update = await client.put(
            f"{self.BASE}/{gid}",
            json={
                "name": "Static Group B",
                "device_serial_numbers": ["SN003"],
            },
        )
        assert update.status_code == 200
        assert update.json()["name"] == "Static Group B"
        assert [d["serial_number"] for d in update.json()["devices"]] == ["SN003"]

        delete = await client.delete(f"{self.BASE}/{gid}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{gid}")
        assert get2.status_code == 404

    async def test_list_distinct(self, client: AsyncClient) -> None:
        await client.post(self.BASE, json={"name": "Static1"})
        await client.post("/api/v1/smart-groups", json={"name": "Smart1"})
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1
        assert all(g["name"] is not None for g in data["items"])

    async def test_update_empty_body(self, client: AsyncClient) -> None:
        create = await client.post(self.BASE, json={"name": "G"})
        gid = create.json()["id"]
        resp = await client.put(f"{self.BASE}/{gid}", json={})
        assert resp.status_code == 200
