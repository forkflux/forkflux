import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.agents.dto import AgentIdentityCreate
from src.agents.exceptions import AgentIdentityConflictError, AgentIdentityNotFoundError
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


async def test_agent_identity_repository_list_returns_identities(db_session: AsyncSession) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-list-role",
        role_label="Agent list role",
    )
    first_identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-list-1",
    )
    second_identity = await AgentIdentityFactory.create(
        db_session,
        role_id=role.id,
        agent_label="agent-list-2",
    )

    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")

    identities = await repository.list()

    identity_ids = {identity.id for identity in identities}

    assert first_identity.id in identity_ids
    assert second_identity.id in identity_ids


async def test_agent_identity_repository_get_by_id_raises_not_found(db_session: AsyncSession) -> None:
    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")

    with pytest.raises(AgentIdentityNotFoundError):
        await repository.get_by_id(agent_identity_id=999_999)


async def test_agent_identity_repository_create_persists_and_returns_identity(db_session: AsyncSession) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-create-role",
        role_label="Agent create role",
    )
    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")
    dto = AgentIdentityCreate(
        agent_label="agent-create-1",
        role_id=role.id,
        tool_family="tools-v1",
    )

    created_identity = await repository.create(dto=dto)

    fetched_identity = await db_session.get(AgentIdentity, created_identity.id)

    assert isinstance(created_identity, AgentIdentity)
    assert created_identity.id is not None
    assert created_identity.agent_label == "agent-create-1"
    assert created_identity.role_id == role.id
    assert created_identity.tool_family == "tools-v1"
    assert created_identity.created_at is not None
    assert fetched_identity is not None
    assert fetched_identity.agent_label == "agent-create-1"
    assert fetched_identity.role_id == role.id
    assert fetched_identity.tool_family == "tools-v1"


async def test_agent_identity_repository_create_raises_conflict_on_integrity_error(db_session: AsyncSession) -> None:
    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")
    dto = AgentIdentityCreate(
        agent_label="agent-create-conflict",
        role_id=999_999,
        tool_family=None,
    )

    with pytest.raises(AgentIdentityConflictError):
        await repository.create(dto=dto)
