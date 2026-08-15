"""Shared fixtures for the MariaDB integration suite (tests-integration/).

This suite runs against a *dedicated* database (INTEGRATION_DB_URL) and
truncates every table between tests, so it must never be pointed at dev or
prod data. Run it via `make test-integration`, which exports DB_URL=INTEGRATION_DB_URL.
"""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text, pool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infra.config.settings import settings
from app.infra.core.base import Base


_REPO_ROOT = Path(__file__).resolve().parents[1]

if not settings.integration_db_url:
    pytest.exit(
        "INTEGRATION_DB_URL is not configured (.env). "
        "Run via `make test-integration` so the suite never targets a dev/prod database.",
        returncode=1,
    )

if settings.db_url != settings.integration_db_url:
    pytest.exit(
        "Refusing to run tests-integration: DB_URL does not match INTEGRATION_DB_URL "
        "(.env). This suite truncates every table between tests. "
        "Run via `make test-integration`, which exports DB_URL=INTEGRATION_DB_URL.",
        returncode=1,
    )

# NullPool: pytest-asyncio uses a fresh event loop per test, and pooled
# connections are bound to the loop they were created on.
test_engine = create_async_engine(settings.db_url, poolclass=pool.NullPool)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


def _ensure_database() -> None:
    """Create the test database if it does not yet exist."""
    import asyncio

    async def _create() -> None:
        url = make_url(settings.db_url)
        server_url = url.set(database=None)
        engine = create_async_engine(server_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{url.database}`"))
        finally:
            await engine.dispose()

    asyncio.run(_create())


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    """Ensure the test DB exists and is migrated to head once per session."""
    _ensure_database()
    command.upgrade(Config(_REPO_ROOT / "alembic.ini"), "head")


@pytest_asyncio.fixture(autouse=True)
async def _truncate_tables() -> AsyncGenerator[None, None]:
    """Truncate every model table after each test.

    The DB is migrated once per session and alembic_version is not part of
    Base.metadata, so it is never truncated.
    """
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        for table in Base.metadata.sorted_tables:
            await conn.execute(text(f"TRUNCATE TABLE `{table.name}`"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        yield session
