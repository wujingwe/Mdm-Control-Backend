from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.core.exceptions import ConflictError
from app.domains.extension_attributes.models import ExtensionAttribute
from app.domains.extension_attributes.schemas import (
    ExtensionAttributeCreate,
    ExtensionAttributeUpdate,
)


class ExtensionAttributeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list(self, skip: int = 0, limit: int = 100) -> list[ExtensionAttribute]:
        stmt = select(ExtensionAttribute).order_by(ExtensionAttribute.id).offset(skip).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, record_id: int) -> ExtensionAttribute | None:
        stmt = select(ExtensionAttribute).where(ExtensionAttribute.id == record_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: ExtensionAttributeCreate, created_by: int) -> ExtensionAttribute:
        instance = ExtensionAttribute(**data.model_dump(), created_by=created_by)
        self._db.add(instance)
        try:
            await self._db.commit()
            await self._db.refresh(instance)
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Extension attribute with this name already exists") from err
        return instance

    async def update(self, record_id: int, data: ExtensionAttributeUpdate) -> int:
        values = data.model_dump(exclude_unset=True)
        if not values:
            return 0
        stmt = update(ExtensionAttribute).where(ExtensionAttribute.id == record_id).values(**values)
        try:
            result = await self._db.execute(stmt)
            await self._db.commit()
        except IntegrityError as err:
            await self._db.rollback()
            raise ConflictError("Extension attribute with this name already exists") from err
        return result.rowcount  # type: ignore

    async def delete(self, record_id: int) -> int:
        stmt = delete(ExtensionAttribute).where(ExtensionAttribute.id == record_id)
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        stmt = select(func.count()).select_from(ExtensionAttribute)
        result = await self._db.execute(stmt)
        return result.scalar_one()
