import pytest
from forkflux_api.agents.dto import TargetRoleCreate
from forkflux_api.agents.exceptions import TargetRoleConflictError, TargetRoleNotFoundError
from forkflux_api.agents.models import TargetRole
from forkflux_api.agents.respositories import TargetRoleRepository
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import TargetRoleFactory


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
