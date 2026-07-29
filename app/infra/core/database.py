from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.infra.config.settings import settings

if settings.mock_db:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_async_engine(
        settings.db_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
