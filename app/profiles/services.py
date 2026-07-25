from app.common.enums import AssignmentStatus
from app.profiles.models import Profile, ProfileAssignment
from app.profiles.repositories import ProfileRepository
from app.profiles.schemas.profile import ProfileCreate, ProfileUpdate, AssignmentUpsert


class ProfileService:
    def __init__(self, repo: ProfileRepository) -> None:
        self.repo = repo

    async def list_profiles(self, skip: int = 0, limit: int = 100) -> tuple[list[Profile], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_profile(self, profile_id: int) -> Profile | None:
        return await self.repo.get_by_id(profile_id)

    async def create_profile(self, data: ProfileCreate, created_by: int) -> Profile:
        return await self.repo.create(data, created_by)

    async def update_profile(self, profile_id: int, data: ProfileUpdate) -> Profile | None:
        return await self.repo.update(profile_id, data)

    async def delete_profile(self, profile_id: int) -> bool:
        return await self.repo.delete(profile_id)

    async def get_assignments(self, profile_id: int) -> list[ProfileAssignment]:
        return await self.repo.get_assignments(profile_id)

    async def update_assignment_status(self, profile_id: int, device_id: int, status: str) -> ProfileAssignment | None:
        from datetime import datetime, timezone

        assignment = await self.repo.get_assignment(profile_id, device_id)
        if not assignment:
            return None
        now = datetime.now(timezone.utc)
        status_enum = AssignmentStatus(status)
        return await self.repo.upsert_assignment(
            AssignmentUpsert(
                profile_id=assignment.profile_id,
                device_id=assignment.device_id,
                desired_state=assignment.desired_state,
                profile_version=assignment.profile_version,
                status=status_enum,
                applied_at=now if status_enum == AssignmentStatus.APPLIED else None,
                revoked_at=now if status_enum == AssignmentStatus.REVOKED else None,
            )
        )
