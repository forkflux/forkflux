from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.models import TargetRole
from src.agents.respositories import TargetRoleRepository
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
