from unittest.mock import AsyncMock, Mock

import pytest
from forkflux_api.agents.dto import (
    AgentApiTokenCreate,
    AgentIdentityCreate,
    AgentIdentityRoleAssign,
    AgentRegistration,
    AgentRegistrationResult,
)
from forkflux_api.agents.exceptions import (
    AgentIdentityConflictError,
    AgentIdentityRoleConflictError,
    TargetRoleNotFoundError,
)
from forkflux_api.agents.services import AgentRegistrationUseCase


def _build_use_case() -> tuple[AgentRegistrationUseCase, dict[str, Mock]]:
    target_role_service = Mock()
    target_role_service.get_roles_by_ids = AsyncMock()
    agent_identity_service = Mock()
    agent_identity_service.create_agent = AsyncMock()
    agent_identity_role_service = Mock()
    agent_identity_role_service.assign_role = AsyncMock()
    agent_api_token_service = Mock()
    agent_api_token_service.create_token = AsyncMock()

    use_case = AgentRegistrationUseCase(
        target_role_service=target_role_service,
        agent_identity_service=agent_identity_service,
        agent_identity_role_service=agent_identity_role_service,
        agent_api_token_service=agent_api_token_service,
        trace_id="trace-123",
    )
    return use_case, {
        "target_role_service": target_role_service,
        "agent_identity_service": agent_identity_service,
        "agent_identity_role_service": agent_identity_role_service,
        "agent_api_token_service": agent_api_token_service,
    }


async def test_register_agent_orchestrates_all_services_and_returns_result() -> None:
    use_case, mocks = _build_use_case()
    dto = AgentRegistration(agent_label="agent-1", tool_family="backend", target_role_ids=[1, 2])

    role_one = Mock(id=1)
    role_two = Mock(id=2)
    mocks["target_role_service"].get_roles_by_ids.return_value = [role_one, role_two]
    created_agent = Mock(id=42)
    mocks["agent_identity_service"].create_agent.return_value = created_agent
    mocks["agent_api_token_service"].create_token.return_value = "raw-token"

    result = await use_case.register_agent(dto)

    mocks["target_role_service"].get_roles_by_ids.assert_awaited_once_with([1, 2])
    mocks["agent_identity_service"].create_agent.assert_awaited_once_with(
        AgentIdentityCreate(agent_label="agent-1", tool_family="backend")
    )
    assert mocks["agent_identity_role_service"].assign_role.await_count == 2
    mocks["agent_identity_role_service"].assign_role.assert_any_await(
        AgentIdentityRoleAssign(agent_identity_id=42, target_role_id=1)
    )
    mocks["agent_identity_role_service"].assign_role.assert_any_await(
        AgentIdentityRoleAssign(agent_identity_id=42, target_role_id=2)
    )
    mocks["agent_api_token_service"].create_token.assert_awaited_once_with(AgentApiTokenCreate(agent_id=42))

    assert isinstance(result, AgentRegistrationResult)
    assert result.agent_id == 42
    assert result.agent_label == "agent-1"
    assert result.tool_family == "backend"
    assert result.target_role_ids == [1, 2]
    assert result.api_token == "raw-token"


async def test_register_agent_supports_none_tool_family() -> None:
    use_case, mocks = _build_use_case()
    dto = AgentRegistration(agent_label="agent-1", tool_family=None, target_role_ids=[1])

    mocks["target_role_service"].get_roles_by_ids.return_value = [Mock(id=1)]
    mocks["agent_identity_service"].create_agent.return_value = Mock(id=7)
    mocks["agent_api_token_service"].create_token.return_value = "raw-token"

    result = await use_case.register_agent(dto)

    assert result.tool_family is None
    assert result.agent_id == 7


async def test_register_agent_raises_not_found_when_role_ids_do_not_exist() -> None:
    use_case, mocks = _build_use_case()
    dto = AgentRegistration(agent_label="agent-1", tool_family="backend", target_role_ids=[1, 999])

    mocks["target_role_service"].get_roles_by_ids.return_value = [Mock(id=1)]

    with pytest.raises(TargetRoleNotFoundError):
        await use_case.register_agent(dto)

    mocks["target_role_service"].get_roles_by_ids.assert_awaited_once_with([1, 999])
    mocks["agent_identity_service"].create_agent.assert_not_called()
    mocks["agent_identity_role_service"].assign_role.assert_not_called()
    mocks["agent_api_token_service"].create_token.assert_not_called()


async def test_register_agent_propagates_identity_conflict_error() -> None:
    use_case, mocks = _build_use_case()
    dto = AgentRegistration(agent_label="agent-dup", tool_family=None, target_role_ids=[1])

    mocks["target_role_service"].get_roles_by_ids.return_value = [Mock(id=1)]
    mocks["agent_identity_service"].create_agent.side_effect = AgentIdentityConflictError

    with pytest.raises(AgentIdentityConflictError):
        await use_case.register_agent(dto)

    mocks["agent_identity_role_service"].assign_role.assert_not_called()
    mocks["agent_api_token_service"].create_token.assert_not_called()


async def test_register_agent_propagates_role_assignment_conflict_error() -> None:
    use_case, mocks = _build_use_case()
    dto = AgentRegistration(agent_label="agent-1", tool_family="backend", target_role_ids=[1])

    mocks["target_role_service"].get_roles_by_ids.return_value = [Mock(id=1)]
    mocks["agent_identity_service"].create_agent.return_value = Mock(id=10)
    mocks["agent_identity_role_service"].assign_role.side_effect = AgentIdentityRoleConflictError

    with pytest.raises(AgentIdentityRoleConflictError):
        await use_case.register_agent(dto)

    mocks["agent_api_token_service"].create_token.assert_not_called()
