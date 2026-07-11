from app.repositories.profile import ProfileRepository
from app.repositories.device import DeviceRepository
from app.repositories.smart_group import SmartGroupRepository


class TestProfileRepository:
    async def test_crud(self, db_session):
        repo = ProfileRepository(db_session)
        created = await repo.create({
            "name": "Test Profile",
            "description": "desc",
            "settings": {"key": "value"},
            "created_by": 1,
        })
        assert created.id is not None
        assert created.name == "Test Profile"
        assert created.settings == {"key": "value"}

        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "Test Profile"

        updated = await repo.update(created.id, {"description": "updated"})
        assert updated.description == "updated"

        assert await repo.count() == 1

    async def test_unique_name(self, db_session):
        import pytest
        from app.core.exceptions import ConflictError
        repo = ProfileRepository(db_session)
        await repo.create({"name": "Dup", "settings": {}, "created_by": 1})
        with pytest.raises(ConflictError):
            await repo.create({"name": "Dup", "settings": {}, "created_by": 1})

    async def test_list(self, db_session):
        repo = ProfileRepository(db_session)
        await repo.create({"name": "P1", "settings": {}, "created_by": 1})
        await repo.create({"name": "P2", "settings": {}, "created_by": 1})
        items = await repo.list_all()
        assert len(items) == 2

    async def test_delete(self, db_session):
        repo = ProfileRepository(db_session)
        created = await repo.create({"name": "X", "settings": {}, "created_by": 1})
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_scope(self, db_session):
        repo = ProfileRepository(db_session)
        profile = await repo.create({"name": "Scoped", "settings": {}, "created_by": 1})
        await repo.set_scope(profile.id, [
            {"target_type": "ALL_DEVICES"},
            {"target_type": "SMART_GROUP", "target_id": 1},
        ])
        scope = await repo.get_scope(profile.id)
        assert len(scope) == 2

    async def test_assignments(self, db_session):
        repo = ProfileRepository(db_session)
        profile = await repo.create({"name": "Assigned", "settings": {}, "created_by": 1})
        assignment = await repo.upsert_assignment({
            "profile_id": profile.id,
            "device_id": 1,
            "source": "DIRECT",
            "status": "PENDING",
            "profile_version": 1,
        })
        assert assignment.id is not None
        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1

    async def test_upsert_assignment_update(self, db_session):
        repo = ProfileRepository(db_session)
        profile = await repo.create({"name": "Upsert", "settings": {}, "created_by": 1})
        await repo.upsert_assignment({
            "profile_id": profile.id,
            "device_id": 1,
            "source": "DIRECT",
            "status": "PENDING",
            "profile_version": 1,
        })
        updated = await repo.upsert_assignment({
            "profile_id": profile.id,
            "device_id": 1,
            "source": "DIRECT",
            "status": "APPLIED",
            "profile_version": 1,
        })
        assert updated.status == "APPLIED"
        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1


class TestProfileAPI:
    BASE = "/api/v1/profiles"

    async def test_crud_flow(self, client):
        create = await client.post(self.BASE, json={
            "name": "Test Profile",
            "description": "desc",
            "settings": {"key": "value"},
        })
        assert create.status_code == 201
        pid = create.json()["id"]
        assert create.json()["name"] == "Test Profile"
        assert create.json()["settings"] == {"key": "value"}

        get = await client.get(f"{self.BASE}/{pid}")
        assert get.status_code == 200
        assert get.json()["name"] == "Test Profile"

        update = await client.put(f"{self.BASE}/{pid}", json={"name": "Updated Profile"})
        assert update.status_code == 200
        assert update.json()["name"] == "Updated Profile"

        delete = await client.delete(f"{self.BASE}/{pid}")
        assert delete.status_code == 200

        get2 = await client.get(f"{self.BASE}/{pid}")
        assert get2.status_code == 404

    async def test_list(self, client):
        await client.post(self.BASE, json={"name": "P1"})
        resp = await client.get(self.BASE)
        data = resp.json()
        assert data["total"] >= 1

    async def test_update_empty_body(self, client):
        create = await client.post(self.BASE, json={"name": "G"})
        pid = create.json()["id"]
        resp = await client.put(f"{self.BASE}/{pid}", json={})
        assert resp.status_code == 400

    async def test_scope_flow(self, client):
        create = await client.post(self.BASE, json={"name": "Scoped Profile"})
        pid = create.json()["id"]

        put_scope = await client.put(f"{self.BASE}/{pid}/scope", json=[
            {"target_type": "ALL_DEVICES"},
        ])
        assert put_scope.status_code == 200
        assert len(put_scope.json()["scope"]) == 1

        get_scope = await client.get(f"{self.BASE}/{pid}/scope")
        assert get_scope.status_code == 200
        assert get_scope.json()["scope"][0]["target_type"] == "ALL_DEVICES"

    async def test_assignments_empty(self, client):
        create = await client.post(self.BASE, json={"name": "No Assignments"})
        pid = create.json()["id"]
        resp = await client.get(f"{self.BASE}/{pid}/assignments")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_update_assignment_status_not_found(self, client):
        create = await client.post(self.BASE, json={"name": "No Assignments"})
        pid = create.json()["id"]
        resp = await client.put(f"{self.BASE}/{pid}/assignments/999/status", json={"status": "APPLIED"})
        assert resp.status_code == 404

    async def test_assignment_recalculation(self, client, db_session):
        device_repo = DeviceRepository(db_session)
        await device_repo.create({
            "name": "Dev1", "serial_number": "SRN-REC-001",
            "os_version": "Android 14", "connection_status": "Online", "enrollment_status": "Compliant",
        })

        sg_repo = SmartGroupRepository(db_session)
        sg = await sg_repo.create({
            "name": "Android 14",
            "created_by": 1,
            "criteria": [
                {"criteria": "os_version", "operator": "is", "type": "string", "value": "Android 14",
                 "left_parentheses": False, "right_parentheses": False},
            ],
        })

        create = await client.post(self.BASE, json={"name": "Recalc Test"})
        pid = create.json()["id"]

        resp = await client.put(f"{self.BASE}/{pid}/scope", json=[
            {"target_type": "SMART_GROUP", "target_id": sg.id},
        ])
        assert resp.status_code == 200

        assignments_resp = await client.get(f"{self.BASE}/{pid}/assignments")
        assert assignments_resp.status_code == 200
        assignments = assignments_resp.json()
        assert len(assignments) == 1
        assert assignments[0]["source"] == "SMART_GROUP"
        assert assignments[0]["status"] == "PENDING"
