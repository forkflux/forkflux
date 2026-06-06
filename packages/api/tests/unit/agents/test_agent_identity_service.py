from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.exceptions import AgentIdentityNotFoundError
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


async def test_agent_identity_service_get_by_id_propagates_not_found_error() -> None:
    repository = Mock()
    repository.get_by_id = AsyncMock(side_effect=AgentIdentityNotFoundError)
    service = AgentIdentityService(agent_identity_repo=repository, trace_id="trace-123")

    with pytest.raises(AgentIdentityNotFoundError):
        await service.get_by_id(agent_identity_id=999_999)

    repository.get_by_id.assert_awaited_once_with(999_999)
