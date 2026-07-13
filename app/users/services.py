from passlib.context import CryptContext

from app.users.models import User
from app.users.repositories import UserRepository
from app.users.schemas import UserCreate, UserUpdate


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return await self.repo.list_all(skip=skip, limit=limit)

    async def get_user(self, user_id: int) -> User | None:
        return await self.repo.get_by_id(user_id)

    async def create_user(self, data: UserCreate) -> User:
        user_data = data.model_dump()
        password = user_data.pop("password")
        user_data["password_hash"] = pwd_context.hash(password)
        return await self.repo.create(user_data)

    async def update_user(self, user_id: int, data: UserUpdate) -> User | None:
        user_data = data.model_dump(exclude_unset=True)
        if "password" in user_data:
            user_data["password_hash"] = pwd_context.hash(user_data.pop("password"))
        if not user_data:
            return None
        return await self.repo.update(user_id, user_data)

    async def delete_user(self, user_id: int) -> bool:
        return await self.repo.delete(user_id)
