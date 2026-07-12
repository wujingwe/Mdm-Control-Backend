from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.smart_groups.models import SmartGroup
from app.policies.models import Policy
from app.smart_groups.repositories import SmartGroupRepository


class SmartGroupService:
    def __init__(self, repo: SmartGroupRepository) -> None:
        self.repo = repo

    async def list_groups(self, skip: int = 0, limit: int = 100) -> list[SmartGroup]:
        return await self.repo.list_all(skip=skip, limit=limit)

    async def get_group(self, group_id: int) -> SmartGroup | None:
        return await self.repo.get_by_id(group_id)

    async def create_group(self, data: dict) -> SmartGroup:
        return await self.repo.create(data)

    async def update_group(self, group_id: int, data: dict) -> SmartGroup | None:
        return await self.repo.update(group_id, data)

    async def delete_group(self, group_id: int) -> bool:
        return await self.repo.delete(group_id)

    async def assign_policy(self, group_id: int, policy_id: int) -> SmartGroup | None:
        db = self.repo.db
        policy = await db.get(Policy, policy_id)
        stmt = select(SmartGroup).where(SmartGroup.id == group_id).options(selectinload(SmartGroup.policies))
        result = await db.execute(stmt)
        group = result.scalar_one_or_none()
        if not group or not policy:
            return None
        if policy not in group.policies:
            group.policies.append(policy)
            await db.commit()
        return group
