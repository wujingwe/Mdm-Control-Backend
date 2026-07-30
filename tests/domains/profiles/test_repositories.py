import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.models import Device
from app.domains.profiles.repositories import ProfileRepository
from app.domains.profiles.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    AssignmentUpsert,
)
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.shared.scope import Scope, ScopeExclusion, ScopeTarget, ScopeType
from app.domains.profiles.schemas.policy import Policy
from app.infra.core.exceptions import ConflictError


class TestProfileRepository:
    async def test_create_profile(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(
            ProfileCreate(name="Prod", description="desc", policy=Policy(), scope=Scope()),
            created_by=1,
        )
        assert created.id is not None
        assert created.name == "Prod"

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "P"

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_list(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        await repo.create(ProfileCreate(name="P1", policy=Policy(), scope=Scope()), created_by=1)
        await repo.create(ProfileCreate(name="P2", policy=Policy(), scope=Scope()), created_by=1)
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        for i in range(5):
            await repo.create(ProfileCreate(name=f"P{i}", policy=Policy(), scope=Scope()), created_by=1)
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_update(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(ProfileCreate(name="P1", policy=Policy(), scope=Scope()), created_by=1)
        updated = await repo.update(created.id, ProfileUpdate(name="P2"))
        assert updated is not None
        assert updated.name == "P2"

    async def test_update_empty_body(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        updated = await repo.update(created.id, ProfileUpdate())
        assert updated is not None
        assert updated.name == "P"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.update(999, ProfileUpdate(name="x")) is None

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.delete(999) is True

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.count() == 0
        await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        assert await repo.count() == 1

    async def test_upsert_assignment_create(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        data = AssignmentUpsert(
            profile_id=profile.id,
            device_id=100,
            status=AssignmentStatus.PENDING,
            profile_version=1,
        )
        result = await repo.upsert_assignment(data)
        assert result.id is not None

    async def test_upsert_assignment_update(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        data = AssignmentUpsert(
            profile_id=profile.id,
            device_id=100,
            status=AssignmentStatus.PENDING,
            profile_version=1,
        )
        await repo.upsert_assignment(data)

        data2 = AssignmentUpsert(
            profile_id=profile.id,
            device_id=100,
            status=AssignmentStatus.APPLIED,
            profile_version=1,
        )
        result = await repo.upsert_assignment(data2)
        assert result.status == AssignmentStatus.APPLIED

    async def test_get_assignments_returns_latest_version(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        await repo.upsert_assignment(
            AssignmentUpsert(
                profile_id=profile.id,
                device_id=100,
                status=AssignmentStatus.APPLIED,
                profile_version=1,
            )
        )
        await repo.upsert_assignment(
            AssignmentUpsert(
                profile_id=profile.id,
                device_id=100,
                status=AssignmentStatus.PENDING,
                profile_version=2,
            )
        )
        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 1
        assert assignments[0].profile_version == 2
        assert assignments[0].status == AssignmentStatus.PENDING

    async def test_get_assignments_multiple_devices(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope()), created_by=1)
        await repo.upsert_assignment(
            AssignmentUpsert(
                profile_id=profile.id,
                device_id=100,
                status=AssignmentStatus.PENDING,
                profile_version=1,
            )
        )
        await repo.upsert_assignment(
            AssignmentUpsert(
                profile_id=profile.id,
                device_id=200,
                status=AssignmentStatus.APPLIED,
                profile_version=1,
            )
        )
        assignments = await repo.get_assignments(profile.id)
        assert len(assignments) == 2

    async def test_list_affected_profiles_for_device(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        device = Device(
            name="Mac",
            serial_number="SN-1",
            os_version="macOS 15",
            connection_status="CONNECTED",
            status="ENROLLED",
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)

        p_all = await repo.create(
            ProfileCreate(
                name="All",
                policy=Policy(),
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.ALL_DEVICES)]),
            ),
            created_by=1,
        )
        await repo.create(ProfileCreate(name="Unrelated", policy=Policy(), scope=Scope()), created_by=1)

        affected = await repo.list_affected_profiles_for_device(device.id)
        assert [profile.id for profile in affected] == [p_all.id]

    async def test_get_assignment(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="GetAssn", policy=Policy(), scope=Scope()), created_by=1)
        await repo.upsert_assignment(
            AssignmentUpsert(profile_id=profile.id, device_id=1, status=AssignmentStatus.PENDING, profile_version=1)
        )
        result = await repo.get_assignment(profile.id, 1)
        assert result is not None
        assert result.device_id == 1

    async def test_get_assignment_not_found(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.get_assignment(999, 1) is None

    async def test_bulk_upsert_assignments(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="Bulk", policy=Policy(), scope=Scope()), created_by=1)
        assignments = [
            AssignmentUpsert(profile_id=profile.id, device_id=1, status=AssignmentStatus.PENDING, profile_version=1),
            AssignmentUpsert(profile_id=profile.id, device_id=2, status=AssignmentStatus.PENDING, profile_version=1),
        ]
        count = await repo.bulk_upsert_assignments(profile.id, assignments)
        assert count == 2
        stored = await repo.get_assignments(profile.id)
        assert len(stored) == 2

    async def test_bulk_upsert_assignments_update_existing(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="BulkUpdate", policy=Policy(), scope=Scope()), created_by=1)
        data = AssignmentUpsert(profile_id=profile.id, device_id=1, status=AssignmentStatus.PENDING, profile_version=1)
        await repo.upsert_assignment(data)
        assignments = [
            AssignmentUpsert(profile_id=profile.id, device_id=1, status=AssignmentStatus.APPLIED, profile_version=1),
        ]
        count = await repo.bulk_upsert_assignments(profile.id, assignments)
        assert count == 1
        stored = await repo.get_assignments(profile.id)
        assert stored[0].status == AssignmentStatus.APPLIED

    async def test_list_affected_profiles_for_none_device(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        affected = await repo.list_affected_profiles_for_device(999)
        assert affected == []

    async def test_list_affected_profiles_device_scope(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        device = Device(
            name="D1", serial_number="SN-D1", os_version="14", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        p_dev = await repo.create(
            ProfileCreate(
                name="DeviceScoped",
                policy=Policy(),
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=device.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_affected_profiles_for_device(device.id)
        assert p_dev.id in [a.id for a in affected]

    async def test_list_affected_profiles_smart_group_scope(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        from app.domains.smart_groups.models import SmartGroup

        sg = SmartGroup(
            name="TestSG",
            criteria=[{"field": "os_version", "operator": "is", "type": "string", "value": "14"}],
            created_by=1,
        )
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        device = Device(
            name="D2", serial_number="SN-D2", os_version="14", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        p_sg = await repo.create(
            ProfileCreate(
                name="SGScoped",
                policy=Policy(),
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.SMART_GROUP, target_id=sg.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_affected_profiles_for_device(device.id)
        assert p_sg.id in [a.id for a in affected]

    async def test_list_affected_profiles_static_group_scope(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        from app.domains.static_groups.models import StaticGroup, StaticGroupDevice

        sg = StaticGroup(name="TestStaticSG", created_by=1)
        db_session.add(sg)
        await db_session.commit()
        await db_session.refresh(sg)
        device = Device(
            name="D3", serial_number="SN-D3", os_version="14", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        db_session.add(StaticGroupDevice(static_group_id=sg.id, device_serial_number="SN-D3"))
        await db_session.commit()
        p_sg = await repo.create(
            ProfileCreate(
                name="StaticSGScoped",
                policy=Policy(),
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.STATIC_GROUP, target_id=sg.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_affected_profiles_for_device(device.id)
        assert p_sg.id in [a.id for a in affected]

    async def test_list_affected_profiles_exclusion_triggers(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        device = Device(
            name="D4", serial_number="SN-D4", os_version="14", connection_status="Connected", status="Enrolled"
        )
        db_session.add(device)
        await db_session.commit()
        await db_session.refresh(device)
        p_excl = await repo.create(
            ProfileCreate(
                name="ExclScope",
                policy=Policy(),
                scope=Scope(exclusions=[ScopeExclusion(scope_type=ScopeType.DEVICE, exclude_id=device.id)]),
            ),
            created_by=1,
        )
        affected = await repo.list_affected_profiles_for_device(device.id)
        assert p_excl.id in [a.id for a in affected]

    async def test_mark_assignment_sent_present(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="MarkSent", policy=Policy(), scope=Scope()), created_by=1)
        data = AssignmentUpsert(
            profile_id=profile.id,
            device_id=1,
            status=AssignmentStatus.PENDING,
            profile_version=1,
            desired_state=AssignmentDesiredState.PRESENT,
        )
        assignment = await repo.upsert_assignment(data)
        await repo.mark_assignment_sent(assignment.id, "msg-1")
        updated = await repo.db.get(type(assignment), assignment.id)
        assert updated.status == AssignmentStatus.SENT

    async def test_mark_assignment_sent_absent(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="MarkSentAbsent", policy=Policy(), scope=Scope()), created_by=1)
        data = AssignmentUpsert(
            profile_id=profile.id,
            device_id=2,
            status=AssignmentStatus.PENDING,
            profile_version=1,
            desired_state=AssignmentDesiredState.ABSENT,
        )
        assignment = await repo.upsert_assignment(data)
        await repo.mark_assignment_sent(assignment.id, "msg-2")
        updated = await repo.db.get(type(assignment), assignment.id)
        assert updated.status == AssignmentStatus.REVOKE_PENDING

    async def test_mark_assignment_failed(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="MarkFailed", policy=Policy(), scope=Scope()), created_by=1)
        data = AssignmentUpsert(
            profile_id=profile.id,
            device_id=3,
            status=AssignmentStatus.PENDING,
            profile_version=1,
        )
        assignment = await repo.upsert_assignment(data)
        await repo.mark_assignment_failed(assignment.id, "something went wrong")
        updated = await repo.db.get(type(assignment), assignment.id)
        assert updated.status == AssignmentStatus.FAILED

    async def test_remove_scope_references(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(
            ProfileCreate(
                name="ToRemove",
                policy=Policy(),
                scope=Scope(targets=[ScopeTarget(scope_type=ScopeType.DEVICE, target_id=42)]),
            ),
            created_by=1,
        )
        affected = await repo.remove_scope_references(ScopeType.DEVICE, 42)
        assert affected == [profile.id]
        updated = await repo.get_by_id(profile.id)
        assert len(updated.scope.targets) == 0

    async def test_remove_scope_references_no_match(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        await repo.create(
            ProfileCreate(name="NotAffected", policy=Policy(), scope=Scope()),
            created_by=1,
        )
        affected = await repo.remove_scope_references(ScopeType.DEVICE, 999)
        assert affected == []

    async def test_create_duplicate_name_raises(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        await repo.create(ProfileCreate(name="Dup", policy=Policy(), scope=Scope()), created_by=1)
        with pytest.raises(ConflictError):
            await repo.create(ProfileCreate(name="Dup", policy=Policy(), scope=Scope()), created_by=1)

    async def test_update_duplicate_name_raises(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        await repo.create(ProfileCreate(name="First", policy=Policy(), scope=Scope()), created_by=1)
        second = await repo.create(ProfileCreate(name="Second", policy=Policy(), scope=Scope()), created_by=1)
        with pytest.raises(ConflictError):
            await repo.update(second.id, ProfileUpdate(name="First"))
