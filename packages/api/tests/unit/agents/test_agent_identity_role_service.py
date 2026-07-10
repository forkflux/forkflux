from unittest.mock import AsyncMock, Mock

import pytest
from forkflux_api.agents.dto import AgentIdentityRoleAssign
from forkflux_api.agents.exceptions import AgentIdentityRoleConflictError, AgentIdentityRoleNotFoundError
from forkflux_api.agents.services import AgentIdentityRoleService


async def test_agent_identity_role_service_init_sets_repository_and_logger() -> None:
    repository = Mock()
    repository.assign = AsyncMock()

    service = AgentIdentityRoleService(agent_identity_role_repo=repository, trace_id="trace-123")

    assert service._agent_identity_role_repo is repository
    assert service._logger is not None


async def test_agent_identity_role_service_assign_role_delegates_and_returns_assignment() -> None:
    dto = AgentIdentityRoleAssign(agent_identity_id=123, target_role_id=456)
    expected_assignment = Mock(id=777)
    repository = Mock()
    repository.assign = AsyncMock(return_value=expected_assignment)
    service = AgentIdentityRoleService(agent_identity_role_repo=repository, trace_id="trace-123")

    assignment = await service.assign_role(dto=dto)

    repository.assign.assert_awaited_once_with(dto)
    assert assignment is expected_assignment


async def test_agent_identity_role_service_assign_role_propagates_conflict_error() -> None:
    dto = AgentIdentityRoleAssign(agent_identity_id=123, target_role_id=456)
    repository = Mock()
    repository.assign = AsyncMock(side_effect=AgentIdentityRoleConflictError)
    service = AgentIdentityRoleService(agent_identity_role_repo=repository, trace_id="trace-123")

    with pytest.raises(AgentIdentityRoleConflictError):
        await service.assign_role(dto=dto)

    repository.assign.assert_awaited_once_with(dto)


async def test_agent_identity_role_service_unassign_role_delegates_and_returns_none() -> None:
    repository = Mock()
    repository.remove = AsyncMock(return_value=None)
    service = AgentIdentityRoleService(agent_identity_role_repo=repository, trace_id="trace-123")

    result = await service.unassign_role(agent_identity_id=123, target_role_id=456)

    repository.remove.assert_awaited_once_with(agent_identity_id=123, target_role_id=456)
    assert result is None


async def test_agent_identity_role_service_unassign_role_propagates_not_found_error() -> None:
    repository = Mock()
    repository.remove = AsyncMock(side_effect=AgentIdentityRoleNotFoundError)
    service = AgentIdentityRoleService(agent_identity_role_repo=repository, trace_id="trace-123")

    with pytest.raises(AgentIdentityRoleNotFoundError):
        await service.unassign_role(agent_identity_id=123, target_role_id=456)

    repository.remove.assert_awaited_once_with(agent_identity_id=123, target_role_id=456)


async def test_agent_identity_role_service_list_role_ids_delegates_and_returns_role_ids() -> None:
    expected_role_ids = [3, 10, 42]
    repository = Mock()
    repository.list_role_ids_for_agent = AsyncMock(return_value=expected_role_ids)
    service = AgentIdentityRoleService(agent_identity_role_repo=repository, trace_id="trace-123")

    role_ids = await service.list_role_ids(agent_identity_id=123)

    repository.list_role_ids_for_agent.assert_awaited_once_with(agent_identity_id=123)
    assert role_ids == expected_role_ids
