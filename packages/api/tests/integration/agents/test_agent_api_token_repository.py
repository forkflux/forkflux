import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.dto import AgentApiTokenCreate
from src.agents.exceptions import AgentApiTokenConflictError, AgentApiTokenNotFoundError
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


async def test_agent_api_token_repository_create_persists_and_returns_token(db_session: AsyncSession) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-token-create-role",
        role_label="Agent token create role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-token-create-1",
    )
    repository = AgentApiTokenRepository(session=db_session, trace_id="trace-123")
    dto = AgentApiTokenCreate(agent_id=identity.id)

    created_token = await repository.create(dto=dto, token_hash="token-create-hash-1")

    fetched_token = await db_session.get(AgentApiToken, created_token.id)

    assert isinstance(created_token, AgentApiToken)
    assert created_token.id is not None
    assert created_token.token_hash == "token-create-hash-1"
    assert created_token.agent_id == identity.id
    assert created_token.is_active is True
    assert created_token.created_at is not None
    assert fetched_token is not None
    assert fetched_token.token_hash == "token-create-hash-1"
    assert fetched_token.agent_id == identity.id
    assert fetched_token.is_active is True


async def test_agent_api_token_repository_create_raises_conflict_on_integrity_error(
    db_session: AsyncSession,
) -> None:
    repository = AgentApiTokenRepository(session=db_session, trace_id="trace-123")
    dto = AgentApiTokenCreate(agent_id=999_999)

    with pytest.raises(AgentApiTokenConflictError):
        await repository.create(dto=dto, token_hash="token-create-conflict")


async def test_agent_api_token_repository_revoke_revokes_all_active_tokens_for_agent(
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-token-revoke-role",
        role_label="Agent token revoke role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-token-revoke-1",
    )
    active_token_1 = await AgentApiTokenFactory.create(
        db_session,
        token_hash="active-revoke-hash-1",
        agent_id=identity.id,
        is_active=True,
    )
    active_token_2 = await AgentApiTokenFactory.create(
        db_session,
        token_hash="active-revoke-hash-2",
        agent_id=identity.id,
        is_active=True,
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash="inactive-revoke-hash-1",
        agent_id=identity.id,
        is_active=False,
    )
    repository = AgentApiTokenRepository(session=db_session, trace_id="trace-123")

    affected_count = await repository.revoke(agent_id=identity.id)

    refreshed_token_1 = await db_session.get(AgentApiToken, active_token_1.id)
    refreshed_token_2 = await db_session.get(AgentApiToken, active_token_2.id)

    assert affected_count == 2
    assert refreshed_token_1 is not None
    assert refreshed_token_2 is not None
    assert refreshed_token_1.is_active is False
    assert refreshed_token_2.is_active is False
    assert refreshed_token_1.revoked_at is not None
    assert refreshed_token_2.revoked_at is not None

    with pytest.raises(AgentApiTokenNotFoundError):
        await repository.get(token_hash="active-revoke-hash-1")

    with pytest.raises(AgentApiTokenNotFoundError):
        await repository.get(token_hash="active-revoke-hash-2")


async def test_agent_api_token_repository_revoke_returns_zero_when_no_active_tokens_exist(
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-token-revoke-role-2",
        role_label="Agent token revoke role 2",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-token-revoke-2",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash="already-revoked-hash-1",
        agent_id=identity.id,
        is_active=False,
    )
    repository = AgentApiTokenRepository(session=db_session, trace_id="trace-123")

    affected_count = await repository.revoke(agent_id=identity.id)

    assert affected_count == 0
