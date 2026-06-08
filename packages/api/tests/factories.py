import hashlib
from datetime import datetime, timezone
from itertools import count
from typing import Any, TypeVar

from polyfactory import AsyncPersistenceProtocol
from polyfactory.factories.sqlalchemy_factory import SQLAASyncPersistence, SQLAlchemyFactory
from polyfactory.fields import Use
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.models import AgentApiToken, AgentIdentity, TargetRole
from src.jobs.constants import JobPriorityEnum, JobStatusEnum
from src.jobs.models import HandoffJob, JobArtifact, JobEvent

T = TypeVar("T")


class CustomSQLAASyncPersistence(SQLAASyncPersistence[Any]):
    async def update(self, data: T) -> T:
        merged_data = await self.session.merge(data)
        await self._flush_or_commit(self.session)
        return merged_data

    async def delete(self, data: T) -> None:
        await self.session.delete(data)
        await self._flush_or_commit(self.session)


class BaseSQLAlchemyFactory(SQLAlchemyFactory[Any]):
    __is_base_factory__ = True
    __async_persistence__ = CustomSQLAASyncPersistence
    __set_primary_key__ = False
    _counter = count(1)

    @classmethod
    def _get_async_persistence(cls) -> AsyncPersistenceProtocol[T]:
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
        return await cls._get_async_persistence().update(data=data)  # type: ignore[attr-defined]

    @classmethod
    async def delete(cls, session: AsyncSession, data: T) -> None:
        cls.__async_session__ = session
        return await cls._get_async_persistence().delete(data=data)  # type: ignore[attr-defined]


class TargetRoleFactory(BaseSQLAlchemyFactory):
    __model__ = TargetRole

    role_key = Use(lambda: f"role-{next(TargetRoleFactory._counter)}")
    created_at: datetime = datetime.now(timezone.utc)


class AgentIdentityFactory(BaseSQLAlchemyFactory):
    __model__ = AgentIdentity

    agent_label = Use(lambda: f"agent-{next(AgentIdentityFactory._counter)}")
    created_at: datetime = datetime.now(timezone.utc)


class AgentApiTokenFactory(BaseSQLAlchemyFactory):
    __model__ = AgentApiToken

    token_hash = Use(lambda: hashlib.sha256(f"raw-token-{next(AgentApiTokenFactory._counter)}".encode()).hexdigest())
    is_active: bool = True
    created_at: datetime = datetime.now(timezone.utc)


class HandoffJobFactory(BaseSQLAlchemyFactory):
    __model__ = HandoffJob

    parent_job_id: int | None = None
    summary = Use(lambda: f"handoff-summary-{next(HandoffJobFactory._counter)}")
    context_payload = Use(lambda: {"source": "factory", "version": 1})
    status: JobStatusEnum = JobStatusEnum.PUBLISHED
    priority: int = JobPriorityEnum.NORMAL.value
    assignee_agent_id: int | None = None
    constraints: list[str] = []
    failure_reason: str | None = None
    published_at: datetime = datetime.now(timezone.utc)
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    cancelled_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)


class JobArtifactFactory(BaseSQLAlchemyFactory):
    __model__ = JobArtifact

    artifact_type = Use(lambda: f"artifact-type-{next(JobArtifactFactory._counter)}")
    artifact_uri = Use(lambda: f"s3://artifacts/job/{next(JobArtifactFactory._counter)}")
    artifact_checksum = Use(
        lambda: hashlib.sha256(f"artifact-{next(JobArtifactFactory._counter)}".encode()).hexdigest()
    )
    metadata_json = Use(lambda: {"source": "factory", "version": 1})
    created_at: datetime = datetime.now(timezone.utc)


class JobEventFactory(BaseSQLAlchemyFactory):
    __model__ = JobEvent

    event_type = Use(lambda: f"event-type-{next(JobEventFactory._counter)}")
    previous_status: JobStatusEnum | None = JobStatusEnum.PUBLISHED
    current_status: JobStatusEnum = JobStatusEnum.CLAIMED
    actor_agent_id: int | None = None
    payload_json = Use(lambda: {"source": "factory", "version": 1})
    created_at: datetime = datetime.now(timezone.utc)
