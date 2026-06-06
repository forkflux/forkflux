import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.exceptions import AgentApiTokenNotFoundError, AgentIdentityNotFoundError
from src.agents.models import AgentApiToken, TargetRole, AgentIdentity


class TargetRoleRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def list(self) -> list[TargetRole]:
        result = await self._session.execute(select(TargetRole))
        return list(result.scalars().all())


class AgentApiTokenRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def get(self, token_hash: str) -> AgentApiToken:
        result = await self._session.execute(
            select(AgentApiToken).where(
                AgentApiToken.token_hash == token_hash,
                AgentApiToken.is_active.is_(True),
            )
        )
        token = result.scalar_one_or_none()
        if token is None:
            raise AgentApiTokenNotFoundError

        return token


class AgentIdentityRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def get_by_id(self, agent_identity_id: int) -> AgentIdentity:
        result = await self._session.execute(select(AgentIdentity).where(AgentIdentity.id == agent_identity_id))
        agent_identity = result.scalar_one_or_none()
        if agent_identity is None:
            raise AgentIdentityNotFoundError

        return agent_identity
