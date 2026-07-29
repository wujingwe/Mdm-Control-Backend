from unittest.mock import AsyncMock, MagicMock

from httpx import AsyncClient

from app.dependencies import get_reconciler
from app.main import app


class TestMobileAppsAPI:
    BASE = "/api/v1/mobile-apps"

    async def test_crud_flow(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "Outlook",
                "enabled": True,
                "package_version": "4.75.0",
                "package_name": "com.microsoft.office.outlook",
                "scope": {"targets": [], "exclusions": []},
            },
        )
        assert create.status_code == 201
        app_id = create.json()["id"]
        assert create.json()["name"] == "Outlook"
        assert create.json()["packageVersion"] == "4.75.0"

        get = await client.get(f"{self.BASE}/{app_id}")
        assert get.status_code == 200
        assert get.json()["name"] == "Outlook"

        update = await client.put(f"{self.BASE}/{app_id}", json={"name": "Outlook2"})
        assert update.status_code == 200
        assert update.json()["name"] == "Outlook2"

        delete = await client.delete(f"{self.BASE}/{app_id}")
        assert delete.status_code == 204

        get2 = await client.get(f"{self.BASE}/{app_id}")
        assert get2.status_code == 404

    async def test_get_not_found(self, client: AsyncClient) -> None:
        resp = await client.get(f"{self.BASE}/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Mobile app not found"

    async def test_update_not_found(self, client: AsyncClient) -> None:
        resp = await client.put(f"{self.BASE}/999", json={"name": "Nope"})
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Mobile app not found"

    async def test_delete_not_found(self, client: AsyncClient) -> None:
        resp = await client.delete(f"{self.BASE}/999")
        assert resp.status_code == 404

    async def test_list(self, client: AsyncClient) -> None:
        await client.post(
            self.BASE,
            json={
                "name": "App1",
                "enabled": True,
                "package_version": "1.0",
                "package_name": "com.app1",
                "scope": {"targets": [], "exclusions": []},
            },
        )
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1

    async def test_create_with_scope_triggers_reconciler(self, client: AsyncClient) -> None:
        reconciler = MagicMock()
        reconciler.recalculate_mobile_app = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.post(
                self.BASE,
                json={
                    "name": "Scoped",
                    "enabled": True,
                    "package_version": "1.0",
                    "package_name": "com.scoped",
                    "scope": {
                        "targets": [{"scope_type": "ALL_DEVICES"}],
                        "exclusions": [],
                    },
                },
            )
        finally:
            app.dependency_overrides.pop(get_reconciler, None)

        assert resp.status_code == 201
        reconciler.recalculate_mobile_app.assert_awaited_once()

    async def test_create_with_empty_scope_skips_reconciler(self, client: AsyncClient) -> None:
        reconciler = MagicMock()
        reconciler.recalculate_mobile_app = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.post(
                self.BASE,
                json={
                    "name": "NoScope",
                    "enabled": True,
                    "package_version": "1.0",
                    "package_name": "com.noscope",
                    "scope": {"targets": [], "exclusions": []},
                },
            )
        finally:
            app.dependency_overrides.pop(get_reconciler, None)

        assert resp.status_code == 201
        reconciler.recalculate_mobile_app.assert_not_called()

    async def test_set_scope(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "App",
                "enabled": True,
                "package_version": "1.0",
                "package_name": "com.app",
                "scope": {"targets": [], "exclusions": []},
            },
        )
        app_id = create.json()["id"]
        resp = await client.put(
            f"{self.BASE}/{app_id}",
            json={
                "scope": {
                    "targets": [{"scope_type": "ALL_DEVICES"}],
                    "exclusions": [],
                },
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["scope"]["targets"]) == 1

    async def test_scope_update_recalculates(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "App",
                "enabled": True,
                "package_version": "1.0",
                "package_name": "com.app",
                "scope": {"targets": [], "exclusions": []},
            },
        )
        app_id = create.json()["id"]

        reconciler = MagicMock()
        reconciler.recalculate_mobile_app = AsyncMock()
        reconciler.recalculate_mobile_apps_for_smart_group = AsyncMock()
        reconciler.recalculate_mobile_apps_for_static_group = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.put(
                f"{self.BASE}/{app_id}",
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
        reconciler.recalculate_mobile_app.assert_awaited_once_with(app_id)

    async def test_update_without_scope_skips_reconciler(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "App",
                "enabled": True,
                "package_version": "1.0",
                "package_name": "com.app",
                "scope": {"targets": [], "exclusions": []},
            },
        )
        app_id = create.json()["id"]

        reconciler = MagicMock()
        reconciler.recalculate_mobile_app = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.put(
                f"{self.BASE}/{app_id}",
                json={"name": "Renamed"},
            )
        finally:
            app.dependency_overrides.pop(get_reconciler, None)

        assert resp.status_code == 200
        reconciler.recalculate_mobile_app.assert_not_called()

    async def test_delete_with_smart_group_scope_triggers_reconciler(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "App",
                "enabled": True,
                "package_version": "1.0",
                "package_name": "com.app",
                "scope": {
                    "targets": [{"scope_type": "SMART_GROUP", "target_id": 1}],
                    "exclusions": [],
                },
            },
        )
        app_id = create.json()["id"]

        reconciler = MagicMock()
        reconciler.recalculate_mobile_apps_for_smart_group = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.delete(f"{self.BASE}/{app_id}")
        finally:
            app.dependency_overrides.pop(get_reconciler, None)

        assert resp.status_code == 409
        reconciler.recalculate_mobile_apps_for_smart_group.assert_awaited_once_with(1)

    async def test_delete_with_static_group_scope_triggers_reconciler(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "App",
                "enabled": True,
                "package_version": "1.0",
                "package_name": "com.app",
                "scope": {
                    "targets": [{"scope_type": "STATIC_GROUP", "target_id": 2}],
                    "exclusions": [],
                },
            },
        )
        app_id = create.json()["id"]

        reconciler = MagicMock()
        reconciler.recalculate_mobile_apps_for_static_group = AsyncMock()
        app.dependency_overrides[get_reconciler] = lambda: reconciler
        try:
            resp = await client.delete(f"{self.BASE}/{app_id}")
        finally:
            app.dependency_overrides.pop(get_reconciler, None)

        assert resp.status_code == 409
        reconciler.recalculate_mobile_apps_for_static_group.assert_awaited_once_with(2)

    async def test_get_assignments_empty(self, client: AsyncClient) -> None:
        create = await client.post(
            self.BASE,
            json={
                "name": "App",
                "enabled": True,
                "package_version": "1.0",
                "package_name": "com.app",
                "scope": {"targets": [], "exclusions": []},
            },
        )
        app_id = create.json()["id"]
        resp = await client.get(f"{self.BASE}/{app_id}/assignments")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_update_assignment_status_not_found(self, client: AsyncClient) -> None:
        resp = await client.put(
            f"{self.BASE}/999/assignments/999/status",
            json={"status": "APPLIED"},
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Assignment not found"
