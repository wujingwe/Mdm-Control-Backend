import re
from collections.abc import AsyncGenerator
from typing import Any

import jwt
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.dependencies import get_db, get_current_user
from app.domains.users.models import User
from app.domains.users.schemas import UserCreate
from app.domains.users.repositories import UserRepository
from app.infra.core.base import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)


@event.listens_for(test_engine.sync_engine, "connect")
def _register_sqlite_regexp(dbapi_conn: Any, _connection_record: Any) -> None:
    dbapi_conn.create_function(
        "regexp",
        2,
        lambda pattern, string: 1 if re.search(pattern, string or "") else 0,
    )


test_async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_async_session() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = override_get_db

    async def _override_current_user() -> User:
        async with test_async_session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_email("test@example.com")
            if not user:
                user = await repo.create(
                    UserCreate(
                        email="test@example.com",
                        name="Test User",
                        permissions=frozenset({"admin"}),
                    )
                )
            return user

    app.dependency_overrides[get_current_user] = _override_current_user

    transport = ASGITransport(app=app)
    token = jwt.encode(
        {"sub": "test@example.com", "email": "test@example.com", "roles": ["admin"]},
        "a-32-byte-long-mock-secret-key!!",
        algorithm="HS256",
    )
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
