import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from forkflux_api.config import get_settings
from forkflux_api.database import Base
from forkflux_api.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

SUPPORTED_TEST_DATABASE_BACKENDS = {"postgresql", "sqlite"}


@pytest.fixture(scope="session", params=SUPPORTED_TEST_DATABASE_BACKENDS)
def test_database_backend(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:18-alpine", driver="asyncpg").with_command(
        "postgres -c max_connections=500"
    ) as container:
        yield container


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment(
    test_database_backend: str,
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[None, None, None]:
    original_database_url = os.environ.get("DATABASE_URL")

    if test_database_backend == "postgresql":
        postgres_container = request.getfixturevalue("postgres_container")
        database_url = postgres_container.get_connection_url()
    else:
        sqlite_db_path = tmp_path_factory.mktemp("integration-db") / "integration.sqlite3"
        database_url = f"sqlite+aiosqlite:///{sqlite_db_path}"

    os.environ["DATABASE_URL"] = database_url
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

    if engine.dialect.name == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

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
        if async_engine.dialect.name == "postgresql":
            table_names = [f'"{table.name}"' for table in Base.metadata.sorted_tables]
            if table_names:
                await conn.execute(text(f"TRUNCATE TABLE {', '.join(table_names)} RESTART IDENTITY CASCADE"))
        else:
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
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app, raise_app_exceptions=True)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
