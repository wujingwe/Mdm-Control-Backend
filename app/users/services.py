from passlib.context import CryptContext

from app.users.models import User
from app.users.repositories import UserRepository


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return await self.repo.list_all(skip=skip, limit=limit)

    async def get_user(self, user_id: int) -> User | None:
        return await self.repo.get_by_id(user_id)

    async def create_user(self, data: dict) -> User:
        password = data.pop("password")
        data["password_hash"] = pwd_context.hash(password)
        return await self.repo.create(data)

    async def update_user(self, user_id: int, data: dict) -> User | None:
        if "password" in data:
            data["password_hash"] = pwd_context.hash(data.pop("password"))
        if not data:
            return None
        return await self.repo.update(user_id, data)

    async def delete_user(self, user_id: int) -> bool:
        return await self.repo.delete(user_id)
