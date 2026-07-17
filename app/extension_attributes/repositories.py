from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.extension_attributes.models import ExtensionAttribute
from app.extension_attributes.schemas import (
    ExtensionAttributeCreate,
    ExtensionAttributeUpdate,
)
from app.core.exceptions import ConflictError


class ExtensionAttributeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[ExtensionAttribute]:
        stmt = (
            select(ExtensionAttribute)
            .order_by(ExtensionAttribute.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> ExtensionAttribute | None:
        stmt = select(ExtensionAttribute).where(ExtensionAttribute.id == record_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: ExtensionAttributeCreate) -> ExtensionAttribute:
        instance = ExtensionAttribute(**data.model_dump())
        self.db.add(instance)
        try:
            await self.db.commit()
            await self.db.refresh(instance)
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError(
                "Extension attribute with this name already exists"
            ) from err  # noqa: TRY003, EM101
        return instance

    async def update(
        self, record_id: int, data: ExtensionAttributeUpdate
    ) -> ExtensionAttribute | None:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return await self.get_by_id(record_id)
        stmt = (
            update(ExtensionAttribute)
            .where(ExtensionAttribute.id == record_id)
            .values(**values)
            .returning(ExtensionAttribute)
        )
        result = await self.db.execute(stmt)
        try:
            await self.db.commit()
        except IntegrityError as err:
            await self.db.rollback()
            raise ConflictError(
                "Extension attribute with this name already exists"
            ) from err  # noqa: TRY003, EM101
        return result.scalars().one_or_none()

    async def delete(self, record_id: int) -> bool:
        stmt = (
            delete(ExtensionAttribute)
            .where(ExtensionAttribute.id == record_id)
            .returning(ExtensionAttribute.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count()).select_from(ExtensionAttribute)
        result = await self.db.execute(stmt)
        return result.scalar_one()
