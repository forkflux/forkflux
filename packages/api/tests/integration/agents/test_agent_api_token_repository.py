from sqlalchemy.ext.asyncio import AsyncSession

import pytest

from src.agents.exceptions import AgentApiTokenNotFoundError
from src.agents.models import AgentApiToken
from src.agents.respositories import AgentApiTokenRepository
from tests.factories import AgentApiTokenFactory, AgentIdentityFactory, TargetRoleFactory


async def test_agent_api_token_repository_init_sets_session_and_logger(db_session: AsyncSession) -> None:
    repository = AgentApiTokenRepository(session=db_session, trace_id="trace-123")

    assert repository._session is db_session
    assert repository._logger is not None


async def test_agent_api_token_repository_get_returns_active_token(db_session: AsyncSession) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-role",
        role_label="Agent role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-1",
    )
    active_token = await AgentApiTokenFactory.create(
        db_session,
        token_hash="active-token-hash",
        agent_id=identity.id,
        is_active=True,
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash="inactive-token-hash",
        agent_id=identity.id,
        is_active=False,
    )

    repository = AgentApiTokenRepository(session=db_session, trace_id="trace-123")

    token = await repository.get(token_hash="active-token-hash")

    assert isinstance(token, AgentApiToken)
    assert token.id == active_token.id
    assert token.token_hash == "active-token-hash"
    assert token.is_active is True


async def test_agent_api_token_repository_get_raises_not_found_for_missing_or_inactive_token(
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-role-2",
        role_label="Agent role 2",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-2",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash="inactive-token-hash-2",
        agent_id=identity.id,
        is_active=False,
    )

    repository = AgentApiTokenRepository(session=db_session, trace_id="trace-123")

    with pytest.raises(AgentApiTokenNotFoundError):
        await repository.get(token_hash="does-not-exist")

    with pytest.raises(AgentApiTokenNotFoundError):
        await repository.get(token_hash="inactive-token-hash-2")
