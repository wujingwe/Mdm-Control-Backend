from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.mobile_apps.models import MobileApp
from app.mobile_apps.schemas import MobileAppCreate, MobileAppUpdate


class MobileAppRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[MobileApp]:
        stmt = select(MobileApp).order_by(MobileApp.id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> MobileApp | None:
        stmt = select(MobileApp).where(MobileApp.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: MobileAppCreate) -> MobileApp:
        instance = MobileApp(**data.model_dump())
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return instance

    async def update(self, record_id: int, data: MobileAppUpdate) -> MobileApp | None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_by_id(record_id)
        stmt = (
            update(MobileApp)
            .where(MobileApp.id == record_id)
            .values(**values)
            .returning(MobileApp)
        )
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError("Resource already exists") from err  # noqa: TRY003, EM101
        return result.scalars().one_or_none()

    async def delete(self, record_id: int) -> bool:
        stmt = (
            delete(MobileApp).where(MobileApp.id == record_id).returning(MobileApp.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(MobileApp)
        result = await self.db.execute(stmt)
        return result.scalar_one()
