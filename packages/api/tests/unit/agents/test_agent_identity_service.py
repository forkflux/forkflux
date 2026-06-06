from unittest.mock import AsyncMock, Mock

import pytest
from src.agents.dto import AgentIdentityCreate
from src.agents.exceptions import AgentIdentityConflictError, AgentIdentityNotFoundError
from src.agents.services import AgentIdentityService


async def test_agent_identity_service_init_sets_repository_and_logger() -> None:
    repository = Mock()
    repository.get_by_id = AsyncMock()

    service = AgentIdentityService(agent_identity_repo=repository, trace_id="trace-123")

    assert service._agent_identity_repo is repository
    assert service._logger is not None


async def test_agent_identity_service_get_by_id_delegates_and_returns_identity() -> None:
    expected_identity = object()
    repository = Mock()
    repository.get_by_id = AsyncMock(return_value=expected_identity)
    service = AgentIdentityService(agent_identity_repo=repository, trace_id="trace-123")

    identity = await service.get_by_id(agent_identity_id=123)

    repository.get_by_id.assert_awaited_once_with(123)
    assert identity is expected_identity


async def test_agent_identity_service_get_all_agents_delegates_and_returns_identities() -> None:
    expected_identities = [object(), object()]
    repository = Mock()
    repository.list = AsyncMock(return_value=expected_identities)
    service = AgentIdentityService(agent_identity_repo=repository, trace_id="trace-123")

    identities = await service.get_all_agents()

    repository.list.assert_awaited_once_with()
    assert identities is expected_identities


async def test_agent_identity_service_get_by_id_propagates_not_found_error() -> None:
    repository = Mock()
    repository.get_by_id = AsyncMock(side_effect=AgentIdentityNotFoundError)
    service = AgentIdentityService(agent_identity_repo=repository, trace_id="trace-123")

    with pytest.raises(AgentIdentityNotFoundError):
        await service.get_by_id(agent_identity_id=999_999)

    repository.get_by_id.assert_awaited_once_with(999_999)


async def test_agent_identity_service_create_agent_delegates_and_returns_identity() -> None:
    dto = AgentIdentityCreate(agent_label="agent-1", role_id=101, tool_family="forkflux")
    expected_identity = object()
    repository = Mock()
    repository.create = AsyncMock(return_value=expected_identity)
    service = AgentIdentityService(agent_identity_repo=repository, trace_id="trace-123")

    identity = await service.create_agent(dto=dto)

    repository.create.assert_awaited_once_with(dto)
    assert identity is expected_identity


async def test_agent_identity_service_create_agent_propagates_conflict_error() -> None:
    dto = AgentIdentityCreate(agent_label="agent-dup", role_id=202, tool_family=None)
    repository = Mock()
    repository.create = AsyncMock(side_effect=AgentIdentityConflictError)
    service = AgentIdentityService(agent_identity_repo=repository, trace_id="trace-123")

    with pytest.raises(AgentIdentityConflictError):
        await service.create_agent(dto=dto)

    repository.create.assert_awaited_once_with(dto)
