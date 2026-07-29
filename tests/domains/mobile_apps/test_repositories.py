from datetime import datetime, timezone

from app.domains.devices.models import Device
from app.domains.mobile_apps.models import MobileAppAssignment
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.mobile_apps.schemas import (
    MobileAppCreate,
    MobileAppUpdate,
    MobileAppAssignmentUpsert,
)
from app.infra.common.enums import AssignmentDesiredState, AssignmentStatus
from app.infra.common.schemas import Scope, ScopeExclusion, ScopeTarget, ScopeType
from sqlalchemy.ext.asyncio import AsyncSession


class TestMobileAppRepository:
    async def test_create(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        created = await repo.create(
            MobileAppCreate(
                name="Outlook",
                enabled=True,
                package_version="4.75.0",
                package_name="com.microsoft.office.outlook",
                scope=Scope(),
            ),
            created_by=1,
        )
        assert created.id is not None
        assert created.name == "Outlook"
        assert created.package_version == "4.75.0"
        assert created.version == 1

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        created = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "App"

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_list_apps(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        await repo.create(
            MobileAppCreate(name="A1", enabled=True, package_version="1.0", package_name="com.a1", scope=Scope()),
            created_by=1,
        )
        await repo.create(
            MobileAppCreate(name="A2", enabled=True, package_version="2.0", package_name="com.a2", scope=Scope()),
            created_by=1,
        )
        items = await repo.list_apps()
        assert len(items) == 2

    async def test_list_apps_pagination(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        for i in range(5):
            await repo.create(
                MobileAppCreate(
                    name=f"App{i}", enabled=True, package_version="1.0", package_name=f"com.app{i}", scope=Scope()
                ),
                created_by=1,
            )
        items = await repo.list_apps(skip=1, limit=2)
        assert len(items) == 2

    async def test_update(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        created = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        updated = await repo.update(created.id, MobileAppUpdate(name="App2", package_version="2.0"))
        assert updated is not None
        assert updated.name == "App2"
        assert updated.package_version == "2.0"
        assert updated.version == 2

    async def test_update_empty_body(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        created = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        updated = await repo.update(created.id, MobileAppUpdate())
        assert updated is not None
        assert updated.name == "App"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        assert await repo.update(999, MobileAppUpdate(name="x")) is None

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        created = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        assert await repo.delete(999) is True

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        assert await repo.count() == 0
        await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        assert await repo.count() == 1

    async def test_upsert_assignment_create(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        data = MobileAppAssignmentUpsert(
            mobile_app_id=app.id,
            device_id=100,
            status=AssignmentStatus.PENDING,
            version=1,
        )
        result = await repo.upsert_assignment(data)
        assert result.id is not None

    async def test_upsert_assignment_update(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        data = MobileAppAssignmentUpsert(
            mobile_app_id=app.id,
            device_id=100,
            status=AssignmentStatus.PENDING,
            version=1,
        )
        await repo.upsert_assignment(data)
        data2 = MobileAppAssignmentUpsert(
            mobile_app_id=app.id,
            device_id=100,
            status=AssignmentStatus.APPLIED,
            version=1,
        )
        result = await repo.upsert_assignment(data2)
        assert result.status == AssignmentStatus.APPLIED

    async def test_get_assignments_returns_latest_version(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=app.id,
                device_id=100,
                status=AssignmentStatus.APPLIED,
                version=1,
            )
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=app.id,
                device_id=100,
                status=AssignmentStatus.PENDING,
                version=2,
            )
        )
        assignments = await repo.get_assignments(app.id)
        assert len(assignments) == 1
        assert assignments[0].version == 2
        assert assignments[0].status == AssignmentStatus.PENDING

    async def test_get_assignments_multiple_devices(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=app.id,
                device_id=100,
                status=AssignmentStatus.PENDING,
                version=1,
            )
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=app.id,
                device_id=200,
                status=AssignmentStatus.APPLIED,
                version=1,
            )
        )
        assignments = await repo.get_assignments(app.id)
        assert len(assignments) == 2

    async def test_list_affected_mobile_apps_for_device(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        device = Device(
            name="iPhone",
            serial_number="SN-1",
            os_version="iOS 18",
            connection_status="CONNECTED",
            status="ENROLLED",
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        app_all = await repo.create(
            MobileAppCreate(
                name="All",
                enabled=True,
                package_version="1.0",
                package_name="com.all",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
            ),
            created_by=1,
        )
        await repo.create(
            MobileAppCreate(name="Unrelated", enabled=True, package_version="1.0", package_name="com.other", scope=Scope()),
            created_by=1,
        )

        affected = await repo.list_affected_mobile_apps_for_device(device.id)
        assert [a.id for a in affected] == [app_all.id]

    async def test_list_affected_for_nonexistent_device(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        affected = await repo.list_affected_mobile_apps_for_device(999)
        assert affected == []

    async def test_get_current_desired_device_ids(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.PENDING, version=1)
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=app.id, device_id=101, status=AssignmentStatus.PENDING, version=1, desired_state=AssignmentDesiredState.ABSENT
            )
        )
        desired = await repo.get_current_desired_device_ids(app.id)
        assert desired == {100}

    async def test_get_current_assignments_for_device(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.PENDING, version=1)
        )
        assignments = await repo.get_current_assignments_for_device(100)
        assert len(assignments) == 1
        assert assignments[0].mobile_app_id == app.id

    async def test_get_assignment_by_version(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.PENDING, version=1)
        )
        result = await repo.get_assignment_by_version(app.id, 100, 1)
        assert result is not None
        assert result.status == AssignmentStatus.PENDING

    async def test_bulk_upsert_assignments(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        count = await repo.bulk_upsert_assignments(app.id, [
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.PENDING, version=1),
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=200, status=AssignmentStatus.PENDING, version=1),
        ])
        assert count == 2

    async def test_bulk_create_assignments(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.bulk_create_assignments(app.id, version=1, device_ids={100, 200}, revoked_device_ids={300})
        assignments = await repo.get_assignments(app.id)
        assert len(assignments) == 3

    async def test_mark_assignment_sent(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.PENDING, version=1)
        )
        assignment = await repo.get_assignment(app.id, 100)
        assert assignment is not None
        await repo.mark_assignment_sent(assignment.id, "msg-1")
        updated = await repo.get_assignment(app.id, 100)
        assert updated is not None
        assert updated.status == AssignmentStatus.SENT
        assert updated.message_id == "msg-1"

    async def test_mark_assignment_sent_nonexistent(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        await repo.mark_assignment_sent(999, "msg-1")

    async def test_mark_assignment_failed(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.PENDING, version=1)
        )
        assignment = await repo.get_assignment(app.id, 100)
        assert assignment is not None
        await repo.mark_assignment_failed(assignment.id, "Something went wrong")
        updated = await repo.get_assignment(app.id, 100)
        assert updated is not None
        assert updated.status == AssignmentStatus.FAILED
        assert updated.last_error == "Something went wrong"

    async def test_mark_assignment_failed_nonexistent(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        await repo.mark_assignment_failed(999, "error")

    async def test_get_max_assignment_version(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        max_ver = await repo.get_max_assignment_version(app.id)
        assert max_ver == 0

    async def test_get_assignment_device_ids_at_version(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.PENDING, version=1)
        )
        ids = await repo.get_assignment_device_ids_at_version(app.id, 1)
        assert ids == {100}

    async def test_remove_scope_references(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(
                name="App",
                enabled=True,
                package_version="1.0",
                package_name="com.app",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=5)]),
            ),
            created_by=1,
        )
        affected = await repo.remove_scope_references(ScopeType.SMART_GROUP, 5)
        assert affected == [app.id]
        updated = await repo.get_by_id(app.id)
        assert updated is not None
        assert len(updated.scope.targets) == 0

    async def test_remove_scope_references_no_match(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(
                name="App",
                enabled=True,
                package_version="1.0",
                package_name="com.app",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=5)]),
            ),
            created_by=1,
        )
        affected = await repo.remove_scope_references(ScopeType.STATIC_GROUP, 5)
        assert affected == []

    async def test_remove_scope_references_exclusions(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(
                name="App",
                enabled=True,
                package_version="1.0",
                package_name="com.app",
                scope=Scope(exclusions=[ScopeExclusion(scope_type=ScopeType.DEVICE, exclude_id=10)]),
            ),
            created_by=1,
        )
        affected = await repo.remove_scope_references(ScopeType.DEVICE, 10)
        assert affected == [app.id]
        updated = await repo.get_by_id(app.id)
        assert updated is not None
        assert len(updated.scope.exclusions) == 0
