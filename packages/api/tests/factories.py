from datetime import datetime, timezone
from typing import TypeVar, Any
from itertools import count

from polyfactory.factories.sqlalchemy_factory import SQLAASyncPersistence, SQLAlchemyFactory
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.models import TargetRole, AgentApiToken, AgentIdentity

T = TypeVar("T")


class CustomSQLAASyncPersistence(SQLAASyncPersistence):

    async def update(self, data: T) -> T:
        merged_data = await self.session.merge(data)
        await self._flush_or_commit(self.session)
        return merged_data

    async def delete(self, data: T) -> None:
        await self.session.delete(data)
        await self._flush_or_commit(self.session)


class BaseSQLAlchemyFactory(SQLAlchemyFactory):
    __is_base_factory__ = True
    __async_persistence__ = CustomSQLAASyncPersistence
    _counter = count(1)

    @classmethod
    def _get_async_persistence(cls):
        if cls.__async_session__ is not None:
            session = cls.__async_session__() if callable(cls.__async_session__) else cls.__async_session__
            return CustomSQLAASyncPersistence(session, persistence_method=cls.__persistence_method__)
        return super()._get_async_persistence()

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs: Any):
        cls.__async_session__ = session
        return await cls.create_async(**kwargs)

    @classmethod
    async def update(cls, session: AsyncSession, data: T) -> T:
        cls.__async_session__ = session
        return await cls._get_async_persistence().update(data=data)

    @classmethod
    async def delete(cls, session: AsyncSession, data: T) -> None:
        cls.__async_session__ = session
        return await cls._get_async_persistence().delete(data=data)


class TargetRoleFactory(BaseSQLAlchemyFactory):
    __model__ = TargetRole

    role_key: str = lambda _: f"role-{next(TargetRoleFactory._counter)}"
    created_at: datetime = datetime.now(timezone.utc)


class AgentIdentityFactory(BaseSQLAlchemyFactory):
    __model__ = AgentIdentity

    agent_label: str = lambda _: f"agent-{next(AgentIdentityFactory._counter)}"
    created_at: datetime = datetime.now(timezone.utc)


class AgentApiTokenFactory(BaseSQLAlchemyFactory):
    __model__ = AgentApiToken

    token_hash: str = lambda _: f"token-hash-{next(AgentApiTokenFactory._counter)}"
    is_active: bool = True
    created_at: datetime = datetime.now(timezone.utc)
