from app.domains.users.models import User
from app.domains.users.repositories import UserRepository
from app.domains.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def list_users(self, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
        items = await self.repo.list(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_user(self, user_id: int) -> User | None:
        return await self.repo.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.repo.get_by_email(email)

    async def create_user(self, data: UserCreate) -> User:
        return await self.repo.create(data)

    async def update_user(self, user_id: int, data: UserUpdate) -> int:
        return await self.repo.update(user_id, data)

    async def delete_user(self, user_id: int) -> int:
        return await self.repo.delete(user_id)
