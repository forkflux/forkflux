from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config
from sqlalchemy.orm import DeclarativeBase, declared_attr

from src.config import get_settings


def get_async_engine(**overrides: str) -> AsyncEngine:
    settings = get_settings()
    config: dict[str, str] = {
        "sqlalchemy.url": settings.database_url,
        "sqlalchemy.echo": overrides.get("sqlalchemy.echo", "false"),
    }

    config.update(overrides)

    return async_engine_from_config(config, prefix="sqlalchemy.", pool_pre_ping=True)


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:  # pragma: no cover - simple convention helper
        return cls.__name__.lower()

    __abstract__ = True
