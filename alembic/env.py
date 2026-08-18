import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.commands import models as command_models
from app.domains.devices import models as device_models
from app.domains.extension_attributes import models as extension_attribute_models
from app.domains.inventory_search import models as inventory_search_models
from app.domains.mobile_apps import models as mobile_app_models
from app.domains.profiles import models as profile_models
from app.domains.smart_groups import models as smart_group_models
from app.domains.static_groups import models as static_group_models
from app.domains.users import models as user_models
from app.infra.config.settings import settings
from app.infra.core.base import Base

_MODEL_MODULES = (
    command_models,
    device_models,
    extension_attribute_models,
    inventory_search_models,
    mobile_app_models,
    profile_models,
    smart_group_models,
    static_group_models,
    user_models,
)


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

if settings.mock_db:
    db_url = "sqlite+aiosqlite:///tmdm.db"
else:
    db_url = settings.db_url
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
