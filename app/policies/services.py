from app.policies.models import Policy
from app.policies.repositories import PolicyRepository


class PolicyService:
    def __init__(self, repo: PolicyRepository) -> None:
        self.repo = repo

    async def list_policies(self, skip: int = 0, limit: int = 100) -> tuple[list[Policy], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_policy(self, policy_id: int) -> Policy | None:
        return await self.repo.get_by_id(policy_id)

    async def create_policy(self, data: dict) -> Policy:
        return await self.repo.create(data)

    async def update_policy(self, policy_id: int, data: dict) -> Policy | None:
        return await self.repo.update(policy_id, data)

    async def delete_policy(self, policy_id: int) -> bool:
        return await self.repo.delete(policy_id)
