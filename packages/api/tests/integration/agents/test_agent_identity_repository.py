import pytest
from forkflux_api.agents.dto import AgentIdentityCreate, AgentIdentityRoleAssign
from forkflux_api.agents.exceptions import (
    AgentIdentityConflictError,
    AgentIdentityNotFoundError,
    AgentIdentityRoleConflictError,
    AgentIdentityRoleNotFoundError,
)
from forkflux_api.agents.models import AgentIdentity, AgentIdentityRole
from forkflux_api.agents.repositories import AgentIdentityRepository, AgentIdentityRoleRepository
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentIdentityFactory, AgentIdentityRoleFactory, TargetRoleFactory


async def test_agent_identity_repository_init_sets_session_and_logger(db_session: AsyncSession) -> None:
    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")

    assert repository._session is db_session
    assert repository._logger is not None


async def test_agent_identity_repository_get_by_id_returns_identity(db_session: AsyncSession) -> None:
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-identity-1",
    )

    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")

    result = await repository.get_by_id(agent_identity_id=identity.id)

    assert isinstance(result, AgentIdentity)
    assert result.id == identity.id
    assert result.agent_label == "agent-identity-1"


async def test_agent_identity_repository_list_returns_identities(db_session: AsyncSession) -> None:
    first_identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-list-1",
    )
    second_identity = await AgentIdentityFactory.create(
        db_session,
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
    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")
    dto = AgentIdentityCreate(
        agent_label="agent-create-1",
        tool_family="tools-v1",
    )

    created_identity = await repository.create(dto=dto)

    fetched_identity = await db_session.get(AgentIdentity, created_identity.id)

    assert isinstance(created_identity, AgentIdentity)
    assert created_identity.id is not None
    assert created_identity.agent_label == "agent-create-1"
    assert created_identity.tool_family == "tools-v1"
    assert created_identity.created_at is not None
    assert fetched_identity is not None
    assert fetched_identity.agent_label == "agent-create-1"
    assert fetched_identity.tool_family == "tools-v1"


async def test_agent_identity_repository_create_raises_conflict_on_integrity_error(db_session: AsyncSession) -> None:
    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")
    dto = AgentIdentityCreate(
        agent_label=None,
        tool_family=None,
    )

    with pytest.raises(AgentIdentityConflictError):
        await repository.create(dto=dto)


async def test_agent_identity_role_repository_assign_persists_and_returns_assignment(db_session: AsyncSession) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-role-assign-role",
        role_label="Agent role assign role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-role-assign-identity",
    )
    repository = AgentIdentityRoleRepository(session=db_session, trace_id="trace-123")
    dto = AgentIdentityRoleAssign(agent_identity_id=identity.id, target_role_id=role.id)

    assignment = await repository.assign(dto=dto)

    fetched_assignment = await db_session.get(AgentIdentityRole, assignment.id)

    assert assignment.id is not None
    assert assignment.agent_identity_id == identity.id
    assert assignment.target_role_id == role.id
    assert assignment.created_at is not None
    assert fetched_assignment is not None
    assert fetched_assignment.agent_identity_id == identity.id
    assert fetched_assignment.target_role_id == role.id


async def test_agent_identity_role_repository_assign_raises_conflict_for_duplicate_pair(
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-role-assign-duplicate-role",
        role_label="Agent role assign duplicate role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-role-assign-duplicate-identity",
    )
    repository = AgentIdentityRoleRepository(session=db_session, trace_id="trace-123")
    dto = AgentIdentityRoleAssign(agent_identity_id=identity.id, target_role_id=role.id)

    await repository.assign(dto=dto)

    with pytest.raises(AgentIdentityRoleConflictError):
        await repository.assign(dto=dto)


async def test_agent_identity_role_repository_list_role_ids_for_agent_returns_sorted_ids(
    db_session: AsyncSession,
) -> None:
    first_role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-role-list-first-role",
        role_label="Agent role list first role",
    )
    second_role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-role-list-second-role",
        role_label="Agent role list second role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-role-list-identity",
    )
    repository = AgentIdentityRoleRepository(session=db_session, trace_id="trace-123")

    await repository.assign(dto=AgentIdentityRoleAssign(agent_identity_id=identity.id, target_role_id=second_role.id))
    await repository.assign(dto=AgentIdentityRoleAssign(agent_identity_id=identity.id, target_role_id=first_role.id))

    role_ids = await repository.list_role_ids_for_agent(agent_identity_id=identity.id)

    assert role_ids == sorted([first_role.id, second_role.id])


async def test_agent_identity_role_repository_remove_deletes_assignment(db_session: AsyncSession) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="agent-role-remove-role",
        role_label="Agent role remove role",
    )
    identity = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-role-remove-identity",
    )
    repository = AgentIdentityRoleRepository(session=db_session, trace_id="trace-123")
    assignment = await repository.assign(
        dto=AgentIdentityRoleAssign(agent_identity_id=identity.id, target_role_id=role.id)
    )

    await repository.remove(agent_identity_id=identity.id, target_role_id=role.id)

    deleted = await db_session.get(AgentIdentityRole, assignment.id)

    assert deleted is None


async def test_agent_identity_role_repository_remove_raises_not_found_for_missing_pair(
    db_session: AsyncSession,
) -> None:
    repository = AgentIdentityRoleRepository(session=db_session, trace_id="trace-123")

    with pytest.raises(AgentIdentityRoleNotFoundError):
        await repository.remove(agent_identity_id=999_999, target_role_id=999_998)


async def test_agent_identity_repository_list_with_roles_returns_agents_with_eagerly_loaded_roles(
    db_session: AsyncSession,
) -> None:
    backend_role = await TargetRoleFactory.create(
        db_session,
        role_key="backend",
        role_label="Backend",
    )
    frontend_role = await TargetRoleFactory.create(
        db_session,
        role_key="frontend",
        role_label="Frontend",
    )
    agent_with_roles = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-with-roles",
    )
    agent_without_roles = await AgentIdentityFactory.create(
        db_session,
        agent_label="agent-without-roles",
    )
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=agent_with_roles.id,
        target_role_id=backend_role.id,
        agent_identity=agent_with_roles,
        target_role=backend_role,
    )
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=agent_with_roles.id,
        target_role_id=frontend_role.id,
        agent_identity=agent_with_roles,
        target_role=frontend_role,
    )

    repository = AgentIdentityRepository(session=db_session, trace_id="trace-123")
    agents = await repository.list_with_roles()

    by_label = {agent.agent_label: agent for agent in agents}

    agent_with = by_label[agent_with_roles.agent_label]
    assert len(agent_with.role_assignments) == 2
    role_keys = {assignment.target_role.role_key for assignment in agent_with.role_assignments}
    role_labels = {assignment.target_role.role_label for assignment in agent_with.role_assignments}
    assert role_keys == {"backend", "frontend"}
    assert role_labels == {"Backend", "Frontend"}

    agent_without = by_label[agent_without_roles.agent_label]
    assert agent_without.role_assignments == []
