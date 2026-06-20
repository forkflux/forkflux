from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_engine_from_config, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.types import TypeDecorator

from forkflux_api.config import get_settings


def get_async_engine(**overrides: str) -> AsyncEngine:
    settings = get_settings()
    config: dict[str, str] = {
        "sqlalchemy.url": settings.database_url,
        "sqlalchemy.echo": overrides.get("sqlalchemy.echo", "false"),
    }

    config.update(overrides)

    return async_engine_from_config(config, prefix="sqlalchemy.", pool_pre_ping=True)


@asynccontextmanager
async def session_manager() -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=get_async_engine(), expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with session_manager() as session:
        yield session


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:  # pragma: no cover - simple convention helper
        return cls.__name__.lower()

    __abstract__ = True


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)
