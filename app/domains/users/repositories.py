from typing import cast

from sqlalchemy import select, func, update, delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate, UserUpdate


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(self, skip: int = 0, limit: int = 100) -> list[User]:
        stmt = select(User).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> User | None:
        stmt = select(User).where(User.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        instance = User(**data.model_dump())
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return instance

    async def update(self, record_id: int, data: UserUpdate) -> User | None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_by_id(record_id)
        stmt = update(User).where(User.id == record_id).values(**values)
        await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err
        return await self.get_by_id(record_id)

    async def delete(self, record_id: int) -> bool:
        stmt = delete(User).where(User.id == record_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return cast(CursorResult, result).rowcount > 0

    async def count(self) -> int:
        stmt = select(func.count()).select_from(User)
        result = await self.db.execute(stmt)
        return result.scalar_one()
