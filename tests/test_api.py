from app.repositories.device import DeviceRepository
from app.repositories.group import GroupRepository
from app.repositories.policy import PolicyRepository
from app.schemas.device import CertificateInfo, NetworkInfo, WifiInfo


class TestDevicesAPI:
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_get_device_not_found(self, client):
        resp = await client.get("/api/v1/devices/999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Device not found"

    async def test_search_devices(self, client):
        resp = await client.post("/api/v1/devices/search", json={"criteria": []})
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_device_response_shape(self, client, db_session):
        repo = DeviceRepository(db_session)
        device = await repo.create({
            "name": "MacBook",
            "serial_number": "SN-API-001",
            "os_version": "15.0",
            "connection_status": "Online",
            "enrollment_status": "Enrolled",
            "network": NetworkInfo(wifi=WifiInfo(ssid="Office")),
            "certificates": [CertificateInfo(common_name="example.com")],
        })
        resp = await client.get(f"/api/v1/devices/{device.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["serial_number"] == "SN-API-001"
        assert body["connection_status"] == "Online"
        assert body["enrollment_status"] == "Enrolled"
        assert "created_at" in body
        assert "updated_at" in body
        assert "last_enrolled_at" in body
        assert body["network"]["wifi"]["ssid"] == "Office"
        assert body["certificates"][0]["common_name"] == "example.com"

class TestDevicePolicyAssignment:
    async def test_assign_policy_device_not_found(self, client):
        resp = await client.post("/api/v1/devices/999/policy", params={"policy_id": 1})
        assert resp.status_code == 404

    async def test_assign_policy_missing_param(self, client):
        resp = await client.post("/api/v1/devices/999/policy")
        assert resp.status_code == 422


class TestPoliciesAPI:
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/policies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_get_policy_not_found(self, client):
        resp = await client.get("/api/v1/policies/999")
        assert resp.status_code == 404

    async def test_list_and_count(self, client):
        resp = await client.get("/api/v1/policies")
        data = resp.json()
        assert "total" in data
        assert "items" in data


class TestGroupsAPI:
    async def test_crud_flow(self, client):
        create = await client.post("/api/v1/groups", json={
            "name": "Group A",
            "description": "desc",
        })
        assert create.status_code == 201
        gid = create.json()["id"]

        get = await client.get(f"/api/v1/groups/{gid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Group A"

        update = await client.put(f"/api/v1/groups/{gid}", json={"name": "Group B"})
        assert update.status_code == 200
        assert update.json()["name"] == "Group B"

        delete = await client.delete(f"/api/v1/groups/{gid}")
        assert delete.status_code == 200

        get2 = await client.get(f"/api/v1/groups/{gid}")
        assert get2.status_code == 404

    async def test_list(self, client):
        await client.post("/api/v1/groups", json={"name": "G1"})
        resp = await client.get("/api/v1/groups")
        data = resp.json()
        assert data["total"] >= 1 and len(data["items"]) >= 1

    async def test_update_empty_body(self, client):
        create = await client.post("/api/v1/groups", json={"name": "G"})
        gid = create.json()["id"]
        resp = await client.put(f"/api/v1/groups/{gid}", json={})
        assert resp.status_code == 400


class TestUsersAPI:
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []

    async def test_get_user_not_found(self, client):
        resp = await client.get("/api/v1/users/999")
        assert resp.status_code == 404

    async def test_get_by_email_not_found(self, client):
        resp = await client.get("/api/v1/users/by-email/nobody@example.com")
        assert resp.status_code == 404


class TestGroupPolicyAssignment:
    async def test_assign_policy_success(self, client, db_session):
        group = await GroupRepository(db_session).create({"name": "Test Group", "created_by": 1})
        policy = await PolicyRepository(db_session).create({
            "name": "Test Policy", "version": 1, "scope": "all",
            "rollout_state": "Completed", "target_devices": 0, "applied_devices": 0,
        })
        resp = await client.post(f"/api/v1/groups/{group.id}/policies", params={"policy_id": policy.id})
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == group.id
        assert data["name"] == "Test Group"

    async def test_assign_policy_group_not_found(self, client):
        resp = await client.post("/api/v1/groups/999/policies", params={"policy_id": 1})
        assert resp.status_code == 404

    async def test_assign_policy_policy_not_found(self, client, db_session):
        group = await GroupRepository(db_session).create({"name": "Test Group", "created_by": 1})
        resp = await client.post(f"/api/v1/groups/{group.id}/policies", params={"policy_id": 999})
        assert resp.status_code == 404

    async def test_assign_policy_missing_param(self, client):
        resp = await client.post("/api/v1/groups/1/policies")
        assert resp.status_code == 422


class TestHealth:
    async def test_liveness(self, client):
        resp = await client.get("/health/live")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_readiness(self, client):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert isinstance(data["uptime_seconds"], int)
        assert data["database"]["status"] == "ok"
        assert isinstance(data["database"]["latency_ms"], float)
        assert data["kafka"] == "disconnected"

    async def test_health_legacy(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"]["status"] == "ok"
        assert data["version"] == "1.0.0"
