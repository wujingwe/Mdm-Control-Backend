from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient

from app.dependencies import get_reconciler
from app.main import app


class TestProfilesAPI:
    BASE = "/api/v1/profiles"

    async def test_crud_flow(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Profile1",
                "description": "desc",
                "policy": {},
                "scope": {"targets": [], "exclusions": []},
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

    async def test_get_not_found(self, client: AsyncClient) -> None:
        resp = await client.get(f"{self.BASE}/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Profile not found"

    async def test_update_not_found(self, client: AsyncClient) -> None:
        resp = await client.put(f"{self.BASE}/999", json={"name": "Nope"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Profile not found"

    async def test_delete_not_found(self, client: AsyncClient) -> None:
        resp = await client.delete(f"{self.BASE}/999")
        assert resp.status_code == 404

    async def test_list(self, client: AsyncClient) -> None:
        await client.post(self.BASE, json={"name": "P1", "policy": {}, "scope": {"targets": [], "exclusions": []}})
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1

    async def test_set_scope(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE, json={"name": "P", "policy": {}, "scope": {"targets": [], "exclusions": []}}
        )
        pid = create.json()["id"]

        reconciler = MagicMock()
        reconciler.request_recalculate_profile = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.put(
                f"{self.BASE}/{pid}",
                json={
                    "scope": {
                        "targets": [{"scope_type": "ALL_DEVICES"}],
                        "exclusions": [],
                    },
                },
            )
        finally:
            app.dependency_overrides.pop(get_reconciler, None)

        assert resp.status_code == 200
        assert len(resp.json()["scope"]["targets"]) == 1
        reconciler.request_recalculate_profile.assert_awaited_once_with(pid)

    async def test_settings_update_forces_recalculation_push(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE, json={"name": "SettingsProfile", "policy": {}, "scope": {"targets": [], "exclusions": []}}
        )
        pid = create.json()["id"]

        reconciler = MagicMock()
        reconciler.request_recalculate_profile = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.put(
                f"{self.BASE}/{pid}",
                json={"policy": {"screenCaptureDisabled": True}},
            )
        finally:
            app.dependency_overrides.pop(get_reconciler, None)

        assert resp.status_code == 200
        reconciler.request_recalculate_profile.assert_awaited_once_with(pid, force_push=True)

    async def test_scope_update_recalculates_without_force_push(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE, json={"name": "ScopeProfile", "policy": {}, "scope": {"targets": [], "exclusions": []}}
        )
        pid = create.json()["id"]

        reconciler = MagicMock()
        reconciler.request_recalculate_profile = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.put(
                f"{self.BASE}/{pid}",
                json={
                    "scope": {
                        "targets": [{"scope_type": "ALL_DEVICES"}],
                        "exclusions": [],
                    }
                },
            )
        finally:
            app.dependency_overrides.pop(get_reconciler, None)

        assert resp.status_code == 200
        reconciler.request_recalculate_profile.assert_awaited_once_with(pid)

    async def test_get_scope(self, client: AsyncClient) -> None:
        reconciler = MagicMock()
        reconciler.request_recalculate_profile = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            create = await client.post(
                self.BASE,
                json={
                    "name": "P2",
                    "policy": {},
                    "scope": {
                        "targets": [{"scope_type": "SMART_GROUP", "target_id": 1}],
                        "exclusions": [],
                    },
                },
            )
            pid = create.json()["id"]
            resp = await client.get(f"{self.BASE}/{pid}")
        finally:
            app.dependency_overrides.pop(get_reconciler, None)
        assert resp.status_code == 200
        assert len(resp.json()["scope"]["targets"]) == 1

    async def test_get_assignments_empty(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE, json={"name": "P", "policy": {}, "scope": {"targets": [], "exclusions": []}}
        )
        pid = create.json()["id"]
        resp = await client.get(f"{self.BASE}/{pid}/assignments")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_update_assignment_status_not_found(self, client: AsyncClient) -> None:
        resp = await client.put(
            f"{self.BASE}/999/assignments/999/status",
            json={"status": "APPLIED"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignment not found"
