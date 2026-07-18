from passlib.context import CryptContext

from app.users.models import User
from app.users.repositories import UserRepository
from app.users.schemas import UserCreate, UserCreateDB, UserUpdate, UserUpdateDB

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def list_users(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[User], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def count_users(self) -> int:
        return await self.repo.count()

    async def get_user(self, user_id: int) -> User | None:
        return await self.repo.get_by_id(user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.repo.get_by_email(email)

    async def create_user(self, data: UserCreate) -> User:
        db_data = UserCreateDB(
            email=data.email,
            name=data.name,
            password_hash=pwd_context.hash(data.password),
            permissions=data.permissions,
        )
        return await self.repo.create(db_data)

    async def update_user(self, user_id: int, data: UserUpdate) -> User | None:
        db_data = UserUpdateDB(
            email=data.email,
            name=data.name,
            password_hash=pwd_context.hash(data.password) if data.password else None,
            permissions=data.permissions,
        )
        if not any(v is not None for v in db_data.model_dump().values()):
            return None
        return await self.repo.update(user_id, db_data)

    async def delete_user(self, user_id: int) -> bool:
        return await self.repo.delete(user_id)
