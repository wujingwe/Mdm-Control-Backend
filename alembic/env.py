import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.config.settings import settings
from app.base import Base
from app.devices.models import Device  # noqa: F401
from app.extension_attributes.models import ExtensionAttribute  # noqa: F401
from app.inventory_search.models import InventorySearch  # noqa: F401
from app.profiles.models import Profile  # noqa: F401
from app.profiles.profile_assignment import ProfileAssignment  # noqa: F401
from app.profiles.profile_scope import ProfileScope  # noqa: F401
from app.smart_groups.models import SmartGroup  # noqa: F401
from app.static_groups.models import StaticGroup  # noqa: F401
from app.static_groups.static_group_device import StaticGroupDevice  # noqa: F401
from app.users.models import User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

config.set_main_option("sqlalchemy.url", settings.db_url)


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
