"""Criteria → SQL predicate generation against MariaDB.

The SQLite unit suite shims `regexp` as a Python re.search fallback, so the
real REGEXP operator is only exercised here.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.devices.models import Device
from app.infra.criteria import Criteria, build_device_query

from helpers import create_device


async def _serials(db_session: AsyncSession, criteria: list[Criteria]) -> list[str]:
    where = build_device_query(criteria)
    stmt = select(Device.serial_number).where(where)
    result = await db_session.execute(stmt)
    return list(result.scalars())


class TestMatchesRegex:
    async def test_regex_matches_subset_of_devices(self, db_session: AsyncSession) -> None:
        await create_device(db_session, "SN-ALPHA-001")
        await create_device(db_session, "SN-ALPHA-002")
        await create_device(db_session, "SN-BETA-001")
        await db_session.commit()

        serials = await _serials(
            db_session,
            [
                Criteria(
                    field="serial_number",
                    operator="matchesRegex",
                    type="string",
                    value="^SN-ALPHA",
                )
            ],
        )
        assert sorted(serials) == ["SN-ALPHA-001", "SN-ALPHA-002"]

    async def test_regex_does_not_match(self, db_session: AsyncSession) -> None:
        await create_device(db_session, "SN-ALPHA-001")
        await create_device(db_session, "SN-BETA-001")
        await db_session.commit()

        serials = await _serials(
            db_session,
            [
                Criteria(
                    field="serial_number",
                    operator="doesNotMatchRegex",
                    type="string",
                    value="^SN-ALPHA",
                )
            ],
        )
        assert serials == ["SN-BETA-001"]

    async def test_regex_requires_full_string_match(self, db_session: AsyncSession) -> None:
        await create_device(db_session, "SN-ALPHA-001")
        await create_device(db_session, "OTHER-SN-ALPHA")
        await db_session.commit()

        serials = await _serials(
            db_session,
            [
                Criteria(
                    field="serial_number",
                    operator="matchesRegex",
                    type="string",
                    value="^SN-ALPHA",
                )
            ],
        )
        assert serials == ["SN-ALPHA-001"]


class TestComparisonOperators:
    async def test_greater_than_filters_devices(self, db_session: AsyncSession) -> None:
        await create_device(db_session, "SN-LOW-BATT")
        await db_session.execute(text("UPDATE devices SET battery_status = 5 WHERE serial_number = 'SN-LOW-BATT'"))
        await create_device(db_session, "SN-HIGH-BATT")
        await db_session.execute(text("UPDATE devices SET battery_status = 90 WHERE serial_number = 'SN-HIGH-BATT'"))
        await db_session.commit()

        serials = await _serials(
            db_session,
            [
                Criteria(
                    field="battery_status",
                    operator="greaterThan",
                    type="number",
                    value="50",
                )
            ],
        )
        assert serials == ["SN-HIGH-BATT"]
