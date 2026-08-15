from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, skip: int = 0, limit: int = 100) -> list[User]:
        stmt = select(User).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> User | None:
        stmt = select(User).where(User.id == record_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        instance = User(**data.model_dump())
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, record_id: int, data: UserUpdate) -> int:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return 0
        stmt = update(User).where(User.id == record_id).values(**values)
        try:
            result = await self._db.execute(stmt)
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Resource already exists") from err
        return result.rowcount  # type: ignore

    async def delete(self, record_id: int) -> int:
        stmt = delete(User).where(User.id == record_id)
        try:
            result = await self._db.execute(stmt)
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("User cannot be deleted because it is referenced by other records") from err
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        stmt = select(func.count()).select_from(User)
        result = await self._db.execute(stmt)
        return result.scalar_one()
