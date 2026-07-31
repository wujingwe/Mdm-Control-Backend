import pytest
from app.domains.devices.models import Device
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.mobile_apps.schemas import (
    MobileAppCreate,
    MobileAppUpdate,
    MobileAppAssignmentUpsert,
)
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.shared.scope import Scope, ScopeExclusion, ScopeTarget, ScopeType
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
        assert await repo.update(created.id, MobileAppUpdate(name="App2", package_version="2.0")) == 1
        updated = await repo.get_by_id(created.id)
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
        assert await repo.update(created.id, MobileAppUpdate()) == 0

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        assert await repo.update(999, MobileAppUpdate(name="x")) == 0

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        created = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        assert await repo.delete(created.id) == 1
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        assert await repo.delete(999) == 0

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

    async def test_upsert_assignment_without_version_updates_latest(self, db_session: AsyncSession) -> None:
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
                version=2,
            )
        )
        result = await repo.upsert_assignment(
            MobileAppAssignmentUpsert(
                mobile_app_id=app.id,
                device_id=100,
                status=AssignmentStatus.APPLIED,
            )
        )
        assert result.version == 2
        assert result.status == AssignmentStatus.APPLIED
        assert len(await repo.get_current_assignments(app.id)) == 1

    async def test_upsert_assignment_rejects_old_version(self, db_session: AsyncSession) -> None:
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
                version=2,
            )
        )
        with pytest.raises(ValueError):
            await repo.upsert_assignment(
                MobileAppAssignmentUpsert(
                    mobile_app_id=app.id,
                    device_id=100,
                    status=AssignmentStatus.PENDING,
                    version=1,
                )
            )
        assert len(await repo.get_current_assignments(app.id)) == 1

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
        assignments = await repo.get_current_assignments(app.id)
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
        assignments = await repo.get_current_assignments(app.id)
        assert len(assignments) == 2

    async def test_get_assignments_latest_version_per_device(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.PENDING, version=1)
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=100, status=AssignmentStatus.APPLIED, version=3)
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=200, status=AssignmentStatus.PENDING, version=2)
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app.id, device_id=200, status=AssignmentStatus.APPLIED, version=5)
        )
        assignments = await repo.get_current_assignments(app.id)
        assert {a.device_id: a.version for a in assignments} == {100: 3, 200: 5}

    async def test_get_assignments_no_leak_across_apps(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app1 = await repo.create(
            MobileAppCreate(name="App1", enabled=True, package_version="1.0", package_name="com.one", scope=Scope()),
            created_by=1,
        )
        app2 = await repo.create(
            MobileAppCreate(name="App2", enabled=True, package_version="1.0", package_name="com.two", scope=Scope()),
            created_by=1,
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app1.id, device_id=100, status=AssignmentStatus.PENDING, version=2)
        )
        await repo.upsert_assignment(
            MobileAppAssignmentUpsert(mobile_app_id=app2.id, device_id=100, status=AssignmentStatus.PENDING, version=2)
        )
        assignments = await repo.get_current_assignments(app1.id)
        assert len(assignments) == 1
        assert assignments[0].mobile_app_id == app1.id

    async def test_list_affected_mobile_apps_all_devices_scope(self, db_session: AsyncSession) -> None:
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
            MobileAppCreate(
                name="Unrelated", enabled=True, package_version="1.0", package_name="com.other", scope=Scope()
            ),
            created_by=1,
        )

        affected = await repo.list_mobile_apps_affected_by_device(device.id)
        assert [a.id for a in affected] == [app_all.id]

    async def test_list_affected_for_nonexistent_device(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        affected = await repo.list_mobile_apps_affected_by_device(999)
        assert affected == []

    async def test_list_affected_mobile_apps_exclusion_only_not_affected(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        device = Device(
            name="iPhone", serial_number="SN-EX", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        app_excl = await repo.create(
            MobileAppCreate(
                name="ExclScope",
                enabled=True,
                package_version="1.0",
                package_name="com.excl",
                scope=Scope(exclusions=[ScopeExclusion(scope_type=ScopeType.DEVICE, exclude_id=device.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_mobile_apps_affected_by_device(device.id)
        assert app_excl.id not in [a.id for a in affected]

    async def test_list_affected_mobile_apps_device_scope(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        device = Device(
            name="iPhone", serial_number="SN-D1", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        app_dev = await repo.create(
            MobileAppCreate(
                name="DeviceScoped",
                enabled=True,
                package_version="1.0",
                package_name="com.dev",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_mobile_apps_affected_by_device(device.id)
        assert app_dev.id in [a.id for a in affected]

    async def test_list_affected_mobile_apps_device_scope_other_device(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        device = Device(
            name="iPhone", serial_number="SN-D1", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        other = Device(
            name="iPhone", serial_number="SN-D2", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        app_dev = await repo.create(
            MobileAppCreate(
                name="DeviceScoped",
                enabled=True,
                package_version="1.0",
                package_name="com.dev",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_mobile_apps_affected_by_device(other.id)
        assert app_dev.id not in [a.id for a in affected]

    async def test_list_affected_mobile_apps_smart_group_scope(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        from app.domains.smart_groups.models import SmartGroup

        sg = SmartGroup(
            name="TestSG",
            criteria=[{"field": "os_version", "operator": "is", "type": "string", "value": "18"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        device = Device(
            name="iPhone", serial_number="SN-D2", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        app_sg = await repo.create(
            MobileAppCreate(
                name="SGScoped",
                enabled=True,
                package_version="1.0",
                package_name="com.sg",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_mobile_apps_affected_by_device(device.id)
        assert app_sg.id in [a.id for a in affected]

    async def test_list_affected_mobile_apps_smart_group_not_member_still_affected(
        self, db_session: AsyncSession
    ) -> None:
        repo = MobileAppRepository(db_session)
        from app.domains.smart_groups.models import SmartGroup

        sg = SmartGroup(
            name="TestSG",
            criteria=[{"field": "os_version", "operator": "is", "type": "string", "value": "99"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        device = Device(
            name="iPhone", serial_number="SN-D2", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        app_sg = await repo.create(
            MobileAppCreate(
                name="SGScoped",
                enabled=True,
                package_version="1.0",
                package_name="com.sg",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_mobile_apps_affected_by_device(device.id)
        assert app_sg.id in [a.id for a in affected]

    async def test_list_affected_mobile_apps_static_group_scope(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        from app.domains.static_groups.models import StaticGroup, StaticGroupDevice

        sg = StaticGroup(name="TestStaticSG", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        device = Device(
            name="iPhone", serial_number="SN-D3", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        db_session.add(StaticGroupDevice(static_group_id=sg.id, device_serial_number="SN-D3"))
        await db_session.commit()
        app_sg = await repo.create(
            MobileAppCreate(
                name="StaticSGScoped",
                enabled=True,
                package_version="1.0",
                package_name="com.static",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_mobile_apps_affected_by_device(device.id)
        assert app_sg.id in [a.id for a in affected]

    async def test_list_affected_mobile_apps_static_group_non_member_not_affected(
        self, db_session: AsyncSession
    ) -> None:
        repo = MobileAppRepository(db_session)
        from app.domains.static_groups.models import StaticGroup

        sg = StaticGroup(name="TestStaticSG", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        device = Device(
            name="iPhone", serial_number="SN-D3", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        app_sg = await repo.create(
            MobileAppCreate(
                name="StaticSGScoped",
                enabled=True,
                package_version="1.0",
                package_name="com.static",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_mobile_apps_affected_by_device(device.id)
        assert app_sg.id not in [a.id for a in affected]

    async def test_list_affected_mobile_apps_target_and_exclusion_still_affected(
        self, db_session: AsyncSession
    ) -> None:
        repo = MobileAppRepository(db_session)
        device = Device(
            name="iPhone", serial_number="SN-D5", os_version="iOS 18", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        app_excl = await repo.create(
            MobileAppCreate(
                name="TargetAndExcl",
                enabled=True,
                package_version="1.0",
                package_name="com.excl",
                scope=Scope(
                    targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)],
                    exclusions=[ScopeExclusion(scope_type=ScopeType.DEVICE, exclude_id=device.id)],
                ),
            ),
            created_by=1,
        )
        affected = await repo.list_mobile_apps_affected_by_device(device.id)
        assert app_excl.id in [a.id for a in affected]

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
                mobile_app_id=app.id,
                device_id=101,
                status=AssignmentStatus.PENDING,
                version=1,
                desired_state=AssignmentDesiredState.ABSENT,
            )
        )
        desired = await repo.get_current_desired_device_ids(app.id)
        assert desired == {100}

    async def test_bulk_create_assignments(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        app = await repo.create(
            MobileAppCreate(name="App", enabled=True, package_version="1.0", package_name="com.app", scope=Scope()),
            created_by=1,
        )
        await repo.bulk_create_assignments(app.id, version=1, device_ids={100, 200}, revoked_device_ids={300})
        assignments = await repo.get_current_assignments(app.id)
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

    async def test_list_mobile_apps_referencing(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        await repo.create(
            MobileAppCreate(
                name="TargetRef",
                enabled=True,
                package_version="1.0",
                package_name="com.target",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=5)]),
            ),
            created_by=1,
        )
        await repo.create(
            MobileAppCreate(
                name="ExclRef",
                enabled=True,
                package_version="1.0",
                package_name="com.excl",
                scope=Scope(exclusions=[ScopeExclusion(scope_type=ScopeType.STATIC_GROUP, exclude_id=5)]),
            ),
            created_by=1,
        )
        await repo.create(
            MobileAppCreate(
                name="NoRef",
                enabled=True,
                package_version="1.0",
                package_name="com.noref",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=99)]),
            ),
            created_by=1,
        )
        refs = await repo.list_mobile_apps_referencing(ScopeType.STATIC_GROUP, 5)
        assert {a.name for a in refs} == {"TargetRef", "ExclRef"}

    async def test_list_mobile_apps_referencing_no_match(self, db_session: AsyncSession) -> None:
        repo = MobileAppRepository(db_session)
        await repo.create(
            MobileAppCreate(
                name="App",
                enabled=True,
                package_version="1.0",
                package_name="com.app",
                scope=Scope(),
            ),
            created_by=1,
        )
        assert await repo.list_mobile_apps_referencing(ScopeType.SMART_GROUP, 999) == []

    async def test_list_mobile_apps_referencing_all_devices_matches_regardless_of_id(
        self, db_session: AsyncSession
    ) -> None:
        repo = MobileAppRepository(db_session)
        await repo.create(
            MobileAppCreate(
                name="AllDevices",
                enabled=True,
                package_version="1.0",
                package_name="com.alldevices",
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
            ),
            created_by=1,
        )
        await repo.create(
            MobileAppCreate(
                name="Other",
                enabled=True,
                package_version="1.0",
                package_name="com.other",
                scope=Scope(),
            ),
            created_by=1,
        )
        assert {a.name for a in await repo.list_mobile_apps_referencing(ScopeType.ALL_DEVICES, 999)} == {"AllDevices"}
