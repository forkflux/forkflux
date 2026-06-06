from sqlalchemy.ext.asyncio import AsyncSession

import pytest

from src.agents.exceptions import AgentIdentityNotFoundError
from src.agents.models import AgentIdentity
from src.agents.respositories import AgentIdentityRepository
from tests.factories import AgentIdentityFactory, TargetRoleFactory


async def test_agent_identity_repository_init_sets_session_and_logger(db_session: AsyncSession) -> None:
    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")

    assert repository._session is db_session
    assert repository._logger is not None


async def test_agent_identity_repository_get_by_id_returns_identity(db_session: AsyncSession) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-role-identity",
        role_label="Agent identity role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-identity-1",
    )

    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")

    result = await repository.get_by_id(agent_identity_id=identity.id)

    assert isinstance(result, AgentIdentity)
    assert result.id == identity.id
    assert result.agent_label == "agent-identity-1"
    assert result.role_id == role.id


async def test_agent_identity_repository_get_by_id_raises_not_found(db_session: AsyncSession) -> None:
    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")

    with pytest.raises(AgentIdentityNotFoundError):
        await repository.get_by_id(agent_identity_id=999_999)
