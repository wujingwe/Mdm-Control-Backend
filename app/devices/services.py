import logging
from collections.abc import Callable
from functools import reduce
from operator import and_, or_

from sqlalchemy import select
from sqlalchemy.sql.expression import BinaryExpression

from app.devices.models import Device
from app.devices.repositories import DeviceRepository
from app.devices.schemas import DeviceSearchCriteria, DeviceUpdate

logger = logging.getLogger(__name__)

_FILTER_BUILDERS: dict[str, Callable] = {
    "is": lambda col, v: col == v,
    "isNot": lambda col, v: col != v,
    "like": lambda col, v: col.like(f"%{v}%"),
    "notLike": lambda col, v: col.not_like(f"%{v}%"),
    "matchesRegex": lambda col, v: col.regexp_match(v),
    "doesNotMatchRegex": lambda col, v: ~col.regexp_match(v),
    "greaterThan": lambda col, v: col.isnot(None) & (col > v),
    "greaterThanOrEqual": lambda col, v: col.isnot(None) & (col >= v),
    "lessThan": lambda col, v: col.isnot(None) & (col < v),
    "lessThanOrEqual": lambda col, v: col.isnot(None) & (col <= v),
}


class DeviceService:
    def __init__(self, repo: DeviceRepository) -> None:
        self.repo = repo

    async def list_devices(
        self, skip: int = 0, limit: int = 100
    ) -> tuple[list[Device], int]:
        items = await self.repo.list_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def get_device(self, device_id: int) -> Device | None:
        return await self.repo.get_by_id(device_id)

    async def update_device(self, device_id: int, data: DeviceUpdate) -> Device | None:
        device = await self.repo.get_by_id(device_id)
        if not device:
            return None
        return await self.repo.update(device_id, data)

    async def search_devices(self, criteria: DeviceSearchCriteria) -> list[Device]:
        db = self.repo.db
        filters: list[BinaryExpression] = []

        for c in criteria.criteria:
            col = getattr(Device, c.get("field", ""), None)
            if col is None:
                continue
            builder = _FILTER_BUILDERS.get(c.get("operator", "is"))
            if builder is not None:
                filters.append(builder(col, c.get("value", "")))

        if not filters:
            stmt = select(Device).order_by(Device.id)
        else:
            combine = and_ if criteria.conjunction == "AND" else or_
            where = reduce(combine, filters)
            stmt = select(Device).where(where).order_by(Device.id)

        result = await db.execute(stmt)
        return list(result.scalars().all())
