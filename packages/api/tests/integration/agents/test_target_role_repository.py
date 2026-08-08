import pytest
from forkflux_api.agents.dto import TargetRoleCreate, TargetRoleUpdate
from forkflux_api.agents.exceptions import TargetRoleConflictError, TargetRoleNotFoundError
from forkflux_api.agents.models import TargetRole
from forkflux_api.agents.repositories import TargetRoleRepository
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentIdentityFactory, AgentIdentityRoleFactory, TargetRoleFactory


async def test_target_role_repository_init_sets_session_and_logger(db_session: AsyncSession) -> None:
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    assert repository._session is db_session
    assert repository._logger is not None


async def test_target_role_repository_list_returns_all_target_roles(db_session: AsyncSession) -> None:
    role_admin = await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    role_viewer = await TargetRoleFactory.create(
        db_session,
        role_key="viewer",
        role_label="Viewer",
    )

    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    roles = await repository.list()

    assert all(isinstance(role, TargetRole) for role in roles)
    assert {role.id for role in roles} == {role_admin.id, role_viewer.id}


async def test_target_role_repository_get_by_role_key_returns_target_role(db_session: AsyncSession) -> None:
    created_role = await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    role = await repository.get_by_role_key(role_key="operator")

    assert isinstance(role, TargetRole)
    assert role.id == created_role.id
    assert role.role_key == "operator"
    assert role.role_label == "Operator"


async def test_target_role_repository_get_by_role_key_raises_not_found(db_session: AsyncSession) -> None:
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    with pytest.raises(TargetRoleNotFoundError):
        await repository.get_by_role_key(role_key="does-not-exist")


async def test_target_role_repository_exists_returns_true_when_role_present(db_session: AsyncSession) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    role_exists = await repository.exists(role_key="operator")

    assert role_exists is True


async def test_target_role_repository_exists_returns_false_when_role_missing(db_session: AsyncSession) -> None:
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    role_exists = await repository.exists(role_key="does-not-exist")

    assert role_exists is False


async def test_target_role_repository_create_persists_and_returns_target_role(db_session: AsyncSession) -> None:
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)
    dto = TargetRoleCreate(role_key="operator", role_label="Operator")
    created_role = await repository.create(dto)

    fetched_role = await db_session.get(TargetRole, created_role.id)

    assert isinstance(created_role, TargetRole)
    assert created_role.id is not None
    assert created_role.role_key == "operator"
    assert created_role.role_label == "Operator"
    assert created_role.created_at is not None
    assert fetched_role is not None
    assert fetched_role.role_key == "operator"
    assert fetched_role.role_label == "Operator"
    assert fetched_role.created_at is not None


async def test_target_role_repository_create_raises_conflict_for_duplicate_role_key(db_session: AsyncSession) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )

    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)
    dto = TargetRoleCreate(role_key="admin", role_label="Admin")

    with pytest.raises(TargetRoleConflictError):
        await repository.create(dto)


async def test_target_role_repository_delete_soft_deletes_role_by_role_id(db_session: AsyncSession) -> None:
    created_role = await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    await repository.delete(role_id=created_role.id)

    # Row must remain with is_deleted=True (soft-delete).
    await db_session.refresh(created_role)
    assert created_role is not None
    assert created_role.is_deleted is True


async def test_target_role_repository_delete_raises_not_found_for_missing_role_id(db_session: AsyncSession) -> None:
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    with pytest.raises(TargetRoleNotFoundError):
        await repository.delete(role_id=999_999)


async def test_target_role_repository_delete_soft_deletes_even_when_role_referenced(
    db_session: AsyncSession,
) -> None:
    role = await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
    )
    agent = await AgentIdentityFactory.create(db_session)
    await AgentIdentityRoleFactory.create(
        db_session,
        agent_identity_id=agent.id,
        target_role_id=role.id,
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    # In-use roles are allowed to soft-delete: the assignment row stays intact
    # and references the now-soft-deleted role id; read paths filter it out.
    await repository.delete(role_id=role.id)

    await db_session.refresh(role)
    assert role.is_deleted is True


async def test_target_role_repository_list_by_ids_returns_matching_roles(db_session: AsyncSession) -> None:
    role_admin = await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    role_viewer = await TargetRoleFactory.create(
        db_session,
        role_key="viewer",
        role_label="Viewer",
    )
    await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    roles = await repository.list_by_ids(ids=[role_admin.id, role_viewer.id])

    assert all(isinstance(role, TargetRole) for role in roles)
    assert {role.id for role in roles} == {role_admin.id, role_viewer.id}


async def test_target_role_repository_list_by_ids_returns_empty_list_when_no_ids_match(
    db_session: AsyncSession,
) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    roles = await repository.list_by_ids(ids=[999_999, 888_888])

    assert roles == []


async def test_target_role_repository_list_by_ids_returns_subset_when_some_ids_missing(
    db_session: AsyncSession,
) -> None:
    role_admin = await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    await TargetRoleFactory.create(
        db_session,
        role_key="viewer",
        role_label="Viewer",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    roles = await repository.list_by_ids(ids=[role_admin.id, 999_999])

    assert all(isinstance(role, TargetRole) for role in roles)
    assert {role.id for role in roles} == {role_admin.id}


async def test_target_role_repository_list_by_ids_returns_empty_list_for_empty_input(
    db_session: AsyncSession,
) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    roles = await repository.list_by_ids(ids=[])

    assert roles == []


async def test_target_role_repository_list_excludes_soft_deleted_roles(db_session: AsyncSession) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    await TargetRoleFactory.create(
        db_session,
        role_key="ghost",
        role_label="Ghost",
        is_deleted=True,
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    roles = await repository.list()

    assert {role.role_key for role in roles} == {"admin"}


async def test_target_role_repository_get_by_role_key_raises_not_found_for_soft_deleted_role(
    db_session: AsyncSession,
) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
        is_deleted=True,
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    with pytest.raises(TargetRoleNotFoundError):
        await repository.get_by_role_key(role_key="operator")


async def test_target_role_repository_exists_returns_false_for_soft_deleted_role(db_session: AsyncSession) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
        is_deleted=True,
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    role_exists = await repository.exists(role_key="operator")

    assert role_exists is False


async def test_target_role_repository_list_by_ids_excludes_soft_deleted_roles(db_session: AsyncSession) -> None:
    active_role = await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    deleted_role = await TargetRoleFactory.create(
        db_session,
        role_key="ghost",
        role_label="Ghost",
        is_deleted=True,
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)

    roles = await repository.list_by_ids(ids=[active_role.id, deleted_role.id])

    assert {role.id for role in roles} == {active_role.id}


async def test_target_role_repository_create_allows_recreating_role_key_after_soft_delete(
    db_session: AsyncSession,
) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin (deleted)",
        is_deleted=True,
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)
    dto = TargetRoleCreate(role_key="admin", role_label="Admin (recreated)")

    recreated_role = await repository.create(dto)

    assert recreated_role.id is not None
    assert recreated_role.role_key == "admin"
    assert recreated_role.role_label == "Admin (recreated)"
    assert recreated_role.is_deleted is False


async def test_target_role_repository_update_updates_role_key_and_label(db_session: AsyncSession) -> None:
    created_role = await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)
    dto = TargetRoleUpdate(role_key="engineer", role_label="Engineer")

    updated_role = await repository.update(role_id=created_role.id, dto=dto)

    assert isinstance(updated_role, TargetRole)
    assert updated_role.id == created_role.id
    assert updated_role.role_key == "engineer"
    assert updated_role.role_label == "Engineer"
    assert updated_role.is_deleted is False

    fetched_role = await db_session.get(TargetRole, created_role.id)
    await db_session.refresh(fetched_role)
    assert fetched_role is not None
    assert fetched_role.role_key == "engineer"
    assert fetched_role.role_label == "Engineer"


async def test_target_role_repository_update_raises_not_found_for_missing_role_id(
    db_session: AsyncSession,
) -> None:
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)
    dto = TargetRoleUpdate(role_key="engineer", role_label="Engineer")

    with pytest.raises(TargetRoleNotFoundError):
        await repository.update(role_id=999_999, dto=dto)


async def test_target_role_repository_update_raises_conflict_when_role_key_taken(
    db_session: AsyncSession,
) -> None:
    await TargetRoleFactory.create(
        db_session,
        role_key="admin",
        role_label="Admin",
    )
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)
    dto = TargetRoleUpdate(role_key="admin", role_label="Administrator")

    with pytest.raises(TargetRoleConflictError):
        await repository.update(role_id=target_role.id, dto=dto)


async def test_target_role_repository_update_raises_not_found_for_soft_deleted_role(
    db_session: AsyncSession,
) -> None:
    soft_deleted_role = await TargetRoleFactory.create(
        db_session,
        role_key="operator",
        role_label="Operator",
        is_deleted=True,
    )
    repository = TargetRoleRepository(trace_id="trace-123", session=db_session)
    dto = TargetRoleUpdate(role_key="engineer", role_label="Engineer")

    with pytest.raises(TargetRoleNotFoundError):
        await repository.update(role_id=soft_deleted_role.id, dto=dto)
