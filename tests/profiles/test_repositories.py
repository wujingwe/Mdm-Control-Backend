from app.profiles.repositories import ProfileRepository
from app.profiles.schemas.profile import (
    ProfileCreate,
    ProfileUpdate,
    AssignmentUpsert,
)
from app.common.enums import AssignmentStatus
from app.common.schemas import Scope
from app.profiles.schemas.policy import Policy
from sqlalchemy.ext.asyncio import AsyncSession


class TestProfileRepository:
    async def test_create_profile(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(
            ProfileCreate(name="Prod", description="desc", policy=Policy(), scope=Scope(), created_by=1)
        )
        assert created.id is not None
        assert created.name == "Prod"

    async def test_get_by_id(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope(), created_by=1))
        found = await repo.get_by_id(created.id)
        assert found is not None
        assert found.name == "P"

    async def test_get_by_id_not_found(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.get_by_id(999) is None

    async def test_list(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        await repo.create(ProfileCreate(name="P1", policy=Policy(), scope=Scope(), created_by=1))
        await repo.create(ProfileCreate(name="P2", policy=Policy(), scope=Scope(), created_by=1))
        items = await repo.list_all()
        assert len(items) == 2

    async def test_list_pagination(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        for i in range(5):
            await repo.create(ProfileCreate(name=f"P{i}", policy=Policy(), scope=Scope(), created_by=1))
        items = await repo.list_all(skip=1, limit=2)
        assert len(items) == 2

    async def test_update(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(ProfileCreate(name="P1", policy=Policy(), scope=Scope(), created_by=1))
        updated = await repo.update(created.id, ProfileUpdate(name="P2"))
        assert updated is not None
        assert updated.name == "P2"

    async def test_update_empty_body(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope(), created_by=1))
        updated = await repo.update(created.id, ProfileUpdate())
        assert updated is not None
        assert updated.name == "P"

    async def test_update_not_found(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.update(999, ProfileUpdate(name="x")) is None

    async def test_delete(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        created = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope(), created_by=1))
        assert await repo.delete(created.id) is True
        assert await repo.get_by_id(created.id) is None

    async def test_delete_not_found(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.delete(999) is True

    async def test_count(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        assert await repo.count() == 0
        await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope(), created_by=1))
        assert await repo.count() == 1

    async def test_upsert_assignment_create(self, db_session: AsyncSession) -> None:
        repo = ProfileRepository(db_session)
        profile = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope(), created_by=1))
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
        profile = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope(), created_by=1))
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
        profile = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope(), created_by=1))
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
        profile = await repo.create(ProfileCreate(name="P", policy=Policy(), scope=Scope(), created_by=1))
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
        from app.common.schemas import Scope, ScopeType, Target
        from app.devices.models import Device

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
                scope=Scope(targets=[Target(scope_type=ScopeType.ALL_DEVICES)]),
            )
        )
        await repo.create(ProfileCreate(name="Unrelated", policy=Policy(), scope=Scope()))

        affected = await repo.list_affected_profiles_for_device(device.id)
        assert [profile.id for profile in affected] == [p_all.id]
