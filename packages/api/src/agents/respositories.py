from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.dto import AgentApiTokenCreate, AgentIdentityCreate, TargetRoleCreate
from src.agents.exceptions import (
    AgentApiTokenConflictError,
    AgentApiTokenNotFoundError,
    AgentIdentityConflictError,
    AgentIdentityNotFoundError,
    TargetRoleConflictError,
    TargetRoleNotFoundError,
)
from src.agents.models import AgentApiToken, AgentIdentity, TargetRole


class TargetRoleRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def list(self) -> list[TargetRole]:
        result = await self._session.execute(select(TargetRole))
        return list(result.scalars().all())

    async def get_by_role_key(self, role_key: str) -> TargetRole:
        result = await self._session.execute(select(TargetRole).where(TargetRole.role_key == role_key))
        target_role = result.scalar_one_or_none()
        if target_role is None:
            raise TargetRoleNotFoundError

        return target_role

    async def create(self, dto: TargetRoleCreate) -> TargetRole:
        target_role = TargetRole(
            role_key=dto.role_key,
            role_label=dto.role_label,
            created_at=datetime.now(timezone.utc),
        )

        self._session.add(target_role)
        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise TargetRoleConflictError from err

        return target_role


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

    async def create(self, dto: AgentApiTokenCreate, token_hash: str) -> AgentApiToken:
        agent_api_token = AgentApiToken(
            token_hash=token_hash,
            agent_id=dto.agent_id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        self._session.add(agent_api_token)
        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise AgentApiTokenConflictError from err

        return agent_api_token

    async def revoke(self, agent_id: int) -> int:
        revoked_at = datetime.now(timezone.utc)
        result = await self._session.execute(
            update(AgentApiToken)
            .where(
                AgentApiToken.agent_id == agent_id,
                AgentApiToken.is_active.is_(True),
            )
            .values(
                is_active=False,
                revoked_at=revoked_at,
            )
        )
        await self._session.flush()

        return result.rowcount or 0  # type: ignore[attr-defined]


class AgentIdentityRepository:
    def __init__(self, session: AsyncSession, trace_id: str) -> None:
        self._session = session
        self._logger = structlog.get_logger().bind(cls=self.__class__.__name__, trace_id=trace_id)

    async def list(self) -> list[AgentIdentity]:
        result = await self._session.execute(select(AgentIdentity))
        return list(result.scalars().all())

    async def get_by_id(self, agent_identity_id: int) -> AgentIdentity:
        result = await self._session.execute(select(AgentIdentity).where(AgentIdentity.id == agent_identity_id))
        agent_identity = result.scalar_one_or_none()
        if agent_identity is None:
            raise AgentIdentityNotFoundError

        return agent_identity

    async def create(self, dto: AgentIdentityCreate) -> AgentIdentity:
        agent_identity = AgentIdentity(
            agent_label=dto.agent_label,
            role_id=dto.role_id,
            tool_family=dto.tool_family,
            created_at=datetime.now(timezone.utc),
        )

        self._session.add(agent_identity)
        try:
            await self._session.flush()
        except IntegrityError as err:
            await self._session.rollback()
            raise AgentIdentityConflictError from err

        return agent_identity
