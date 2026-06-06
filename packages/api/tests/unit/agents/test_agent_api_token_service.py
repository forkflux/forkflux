from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.exceptions import AgentApiTokenNotFoundError
from src.agents.services import AgentApiTokenService


async def test_agent_api_token_service_init_sets_repository_and_logger() -> None:
    repository = Mock()
    repository.get = AsyncMock()

    service = AgentApiTokenService(agent_api_token_repo=repository, trace_id="trace-123")

    assert service._agent_api_token_repo is repository
    assert service._logger is not None


async def test_agent_api_token_service_get_token_delegates_and_returns_token() -> None:
    expected_token = object()
    repository = Mock()
    repository.get = AsyncMock(return_value=expected_token)
    service = AgentApiTokenService(agent_api_token_repo=repository, trace_id="trace-123")

    token = await service.get_token(token_hash="token-hash-123")

    repository.get.assert_awaited_once_with("token-hash-123")
    assert token is expected_token


async def test_agent_api_token_service_get_token_propagates_not_found_error() -> None:
    repository = Mock()
    repository.get = AsyncMock(side_effect=AgentApiTokenNotFoundError)
    service = AgentApiTokenService(agent_api_token_repo=repository, trace_id="trace-123")

    with pytest.raises(AgentApiTokenNotFoundError):
        await service.get_token(token_hash="missing-token-hash")

    repository.get.assert_awaited_once_with("missing-token-hash")
