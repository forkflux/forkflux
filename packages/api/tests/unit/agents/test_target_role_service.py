from unittest.mock import AsyncMock, Mock

from src.agents.services import TargetRoleService


async def test_target_role_service_init_sets_repository_and_logger() -> None:
    repository = Mock()
    repository.list = AsyncMock(return_value=[])

    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    assert service._target_role_repo is repository
    assert service._logger is not None


async def test_target_role_service_get_all_roles_delegates_and_returns_roles() -> None:
    expected_roles = [object(), object()]
    repository = Mock()
    repository.list = AsyncMock(return_value=expected_roles)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    roles = await service.get_all_roles()

    repository.list.assert_awaited_once_with()
    assert roles == expected_roles
