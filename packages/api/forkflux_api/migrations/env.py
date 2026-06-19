import logging.config
import pathlib
import sys
from typing import TYPE_CHECKING

import alembic_postgresql_enum  # noqa: F401

# Import all models so that Base.metadata is populated for autogenerate.
import forkflux_api.agents.models  # noqa: F401
import forkflux_api.jobs.models  # noqa: F401
from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from forkflux_api.config import get_settings
from forkflux_api.database import Base, get_async_engine

target_metadata = Base.metadata

if TYPE_CHECKING:
    from sqlalchemy.engine.base import Connection


logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "generic": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "generic",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "alembic": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }
)


def run_migrations_offline() -> None:
    settings = get_settings()

    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: "Connection") -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine: AsyncEngine = get_async_engine()

    async with engine.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await engine.dispose()


def run_migrations() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        import asyncio

        asyncio.run(run_migrations_online())


run_migrations()
