import os
from typing import Generator, AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from testcontainers.postgres import PostgresContainer

from src.config import get_settings
from src.database import Base
from src.main import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:18-alpine", driver="asyncpg").with_command(
        "postgres -c max_connections=500"
    ) as container:
        yield container


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment(postgres_container: PostgresContainer) -> Generator[None, None, None]:
    original_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = postgres_container.get_connection_url()
    get_settings.cache_clear()

    yield

    if original_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = original_database_url

    get_settings.cache_clear()

@pytest.fixture(scope="session")
async def async_engine(configure_test_environment) -> AsyncGenerator[AsyncEngine, None]:
    """Global Engine with NullPool for speed."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def setup_db(async_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Create DB schema (DDL)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(scope="function", autouse=True)
async def clean_database(async_engine: AsyncEngine):
    async with async_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield


@pytest.fixture(scope="function")
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session



@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
