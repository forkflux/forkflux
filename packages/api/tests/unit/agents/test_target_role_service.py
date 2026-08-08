from unittest.mock import AsyncMock, Mock

import pytest
from forkflux_api.agents.dto import TargetRoleCreate, TargetRoleUpdate
from forkflux_api.agents.exceptions import TargetRoleConflictError, TargetRoleNotFoundError
from forkflux_api.agents.services import TargetRoleService


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


async def test_target_role_service_get_roles_by_ids_delegates_and_returns_roles() -> None:
    role_ids = [1, 2, 3]
    expected_roles = [object(), object(), object()]
    repository = Mock()
    repository.list_by_ids = AsyncMock(return_value=expected_roles)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    roles = await service.get_roles_by_ids(role_ids)

    repository.list_by_ids.assert_awaited_once_with(role_ids)
    assert roles == expected_roles


async def test_target_role_service_create_role_delegates_and_returns_role() -> None:
    dto = TargetRoleCreate(role_key="frontend_engineer", role_label="Frontend Engineer")
    expected_role = object()
    repository = Mock()
    repository.create = AsyncMock(return_value=expected_role)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    role = await service.create_role(dto)

    repository.create.assert_awaited_once_with(dto)
    assert role == expected_role


async def test_target_role_service_get_by_role_key_delegates_and_returns_role() -> None:
    expected_role = object()
    repository = Mock()
    repository.get_by_role_key = AsyncMock(return_value=expected_role)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    role = await service.get_by_role_key("frontend_engineer")

    repository.get_by_role_key.assert_awaited_once_with("frontend_engineer")
    assert role == expected_role


async def test_target_role_service_get_by_role_key_propagates_not_found() -> None:
    repository = Mock()
    repository.get_by_role_key = AsyncMock(side_effect=TargetRoleNotFoundError)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    with pytest.raises(TargetRoleNotFoundError):
        await service.get_by_role_key("missing")


async def test_target_role_service_is_role_exists_returns_true() -> None:
    repository = Mock()
    repository.exists = AsyncMock(return_value=True)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    result = await service.is_role_exists("frontend_engineer")

    repository.exists.assert_awaited_once_with("frontend_engineer")
    assert result is True


async def test_target_role_service_is_role_exists_returns_false() -> None:
    repository = Mock()
    repository.exists = AsyncMock(return_value=False)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    result = await service.is_role_exists("nonexistent")

    repository.exists.assert_awaited_once_with("nonexistent")
    assert result is False


async def test_target_role_service_delete_role_delegates_and_returns_none() -> None:
    role_id = 1
    repository = Mock()
    repository.delete = AsyncMock(return_value=None)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    result = await service.delete_role(role_id)

    repository.delete.assert_awaited_once_with(role_id)
    assert result is None


async def test_target_role_service_delete_role_propagates_not_found_for_missing_role() -> None:
    role_id = 999
    repository = Mock()
    repository.delete = AsyncMock(side_effect=TargetRoleNotFoundError)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    with pytest.raises(TargetRoleNotFoundError):
        await service.delete_role(role_id)

    repository.delete.assert_awaited_once_with(role_id)


async def test_target_role_service_update_role_delegates_and_returns_role() -> None:
    role_id = 1
    dto = TargetRoleUpdate(role_key="engineer", role_label="Engineer")
    expected_role = object()
    repository = Mock()
    repository.update = AsyncMock(return_value=expected_role)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    role = await service.update_role(role_id, dto)

    repository.update.assert_awaited_once_with(role_id, dto)
    assert role == expected_role


async def test_target_role_service_update_role_propagates_not_found_for_missing_role() -> None:
    role_id = 999
    dto = TargetRoleUpdate(role_key="engineer", role_label="Engineer")
    repository = Mock()
    repository.update = AsyncMock(side_effect=TargetRoleNotFoundError)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    with pytest.raises(TargetRoleNotFoundError):
        await service.update_role(role_id, dto)

    repository.update.assert_awaited_once_with(role_id, dto)


async def test_target_role_service_update_role_propagates_conflict_for_taken_role_key() -> None:
    role_id = 1
    dto = TargetRoleUpdate(role_key="admin", role_label="Administrator")
    repository = Mock()
    repository.update = AsyncMock(side_effect=TargetRoleConflictError)
    service = TargetRoleService(target_role_repo=repository, trace_id="trace-123")

    with pytest.raises(TargetRoleConflictError):
        await service.update_role(role_id, dto)

    repository.update.assert_awaited_once_with(role_id, dto)
